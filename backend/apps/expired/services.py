from collections import defaultdict
from decimal import Decimal
from operator import itemgetter

from django.urls import reverse

from apps.distribution.models import DistributionItem
from apps.stock.models import Transaction

from .forms import ExpiredAuditReportForm
from .models import Expired, ExpiredItem


def generate_expired_audit_report(filters):
    outcome_type = filters.get(
        "outcome_type", ExpiredAuditReportForm.OutcomeType.BOTH
    )
    rows = []

    if outcome_type in {
        ExpiredAuditReportForm.OutcomeType.BOTH,
        ExpiredAuditReportForm.OutcomeType.OUT,
    }:
        rows.extend(_build_distribution_rows(filters))

    if outcome_type in {
        ExpiredAuditReportForm.OutcomeType.BOTH,
        ExpiredAuditReportForm.OutcomeType.DESTROY,
    }:
        rows.extend(_build_destroy_rows(filters))

    rows.sort(
        key=lambda row: (
            row["event_timestamp"],
            row["document_number"],
            row["item_name"],
            row["batch_lot"],
            row["reference_identifier"],
        )
    )

    summary = _build_summary(rows)

    return {
        "rows": rows,
        "summary_by_outcome": summary["summary_by_outcome"],
        "summary_by_item": summary["summary_by_item"],
        "reconciliation_rows": summary["reconciliation_rows"],
        "total_rows": len(rows),
    }


def _build_distribution_rows(filters):
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    location = filters.get("location")
    facility = filters.get("facility")
    item = filters.get("item")
    funding_source = filters.get("funding_source")

    queryset = (
        DistributionItem.objects.filter(
            distribution__status="DISTRIBUTED",
            distribution__distributed_date__range=[start_date, end_date],
        )
        .select_related(
            "distribution",
            "distribution__facility",
            "distribution__approved_by",
            "item",
            "item__satuan",
            "stock",
            "stock__location",
            "issued_sumber_dana",
        )
        .order_by(
            "distribution__distributed_date",
            "distribution__document_number",
            "item__nama_barang",
            "issued_batch_lot",
        )
    )

    if item:
        queryset = queryset.filter(item=item)

    if facility:
        queryset = queryset.filter(distribution__facility=facility)

    if location:
        queryset = queryset.filter(stock__location=location)

    if funding_source:
        queryset = queryset.filter(issued_sumber_dana=funding_source)

    # This report is scoped to expired batches that left stock via an OUT path.
    # OUT rows are filtered by distribution event date, while destroy rows are
    # filtered by disposal timestamp; the extra expiry-date condition ensures the
    # OUT side only contributes batches that were already expired in the selected
    # reporting window before they left inventory.
    queryset = queryset.filter(
        issued_expiry_date__isnull=False,
        issued_expiry_date__lte=end_date,
    )

    distribution_ids = queryset.values_list("distribution_id", flat=True).distinct()
    transaction_map = _build_distribution_transaction_map(distribution_ids)

    rows = []
    for distribution_item in queryset:
        quantity = (
            distribution_item.quantity_approved
            if distribution_item.quantity_approved is not None
            else distribution_item.quantity_requested
        )
        batch_lot = distribution_item.issued_batch_lot or (
            distribution_item.stock.batch_lot if distribution_item.stock else ""
        )
        transaction = _pop_distribution_transaction(
            transaction_map,
            distribution_item.distribution_id,
            distribution_item.item_id,
            batch_lot,
            quantity,
        )
        distribution = distribution_item.distribution
        stock = distribution_item.stock
        funding = distribution_item.issued_sumber_dana
        location_obj = _resolve_location(stock, transaction)
        responsible_user = _resolve_responsible_user(transaction, distribution)
        event_timestamp = _resolve_event_timestamp(transaction, distribution)

        rows.append(
            {
                "row_type": "DETAIL",
                "outcome_type": ExpiredAuditReportForm.OutcomeType.OUT,
                "outcome_label": "OUT (Distribusi)",
                "document_type": "Distribusi",
                "document_number": distribution.document_number,
                "document_url": reverse(
                    "distribution:distribution_detail", args=[distribution.pk]
                ),
                "item_code": distribution_item.item.kode_barang,
                "item_name": distribution_item.item.nama_barang,
                "item_display": _build_item_display(distribution_item.item),
                "batch_lot": batch_lot or "-",
                "expiry_date": distribution_item.issued_expiry_date,
                "quantity": quantity,
                "unit_name": (
                    distribution_item.item.satuan.name
                    if distribution_item.item.satuan
                    else "-"
                ),
                "location_name": location_obj.name if location_obj else "-",
                "facility_name": (
                    distribution.facility.name if distribution.facility else "-"
                ),
                "funding_source_name": funding.name if funding else "-",
                "responsible_user": _display_user(responsible_user),
                "event_timestamp": event_timestamp,
                "event_date": event_timestamp.date() if event_timestamp else None,
                "notes": distribution_item.notes or distribution.notes or "-",
                "reference_identifier": transaction.pk if transaction else "",
                "reference_label": (
                    f"TRX-{transaction.pk}" if transaction else "Distribusi"
                ),
            }
        )

    return rows


def _build_destroy_rows(filters):
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    location = filters.get("location")
    item = filters.get("item")
    funding_source = filters.get("funding_source")

    queryset = (
        ExpiredItem.objects.filter(
            expired__status=Expired.Status.DISPOSED,
            expired__disposed_at__date__range=[start_date, end_date],
        )
        .select_related(
            "expired",
            "expired__disposed_by",
            "expired__verified_by",
            "item",
            "item__satuan",
            "stock",
            "stock__location",
            "stock__sumber_dana",
        )
        .order_by(
            "expired__disposed_at",
            "expired__document_number",
            "item__nama_barang",
            "stock__batch_lot",
        )
    )

    if item:
        queryset = queryset.filter(item=item)

    if location:
        queryset = queryset.filter(stock__location=location)

    if funding_source:
        queryset = queryset.filter(stock__sumber_dana=funding_source)

    rows = []
    for expired_item in queryset:
        expired_doc = expired_item.expired
        stock = expired_item.stock
        event_timestamp = expired_doc.disposed_at or expired_doc.verified_at
        responsible_user = expired_doc.disposed_by or expired_doc.verified_by

        rows.append(
            {
                "row_type": "DETAIL",
                "outcome_type": ExpiredAuditReportForm.OutcomeType.DESTROY,
                "outcome_label": "Destroy (Kedaluwarsa)",
                "document_type": "Expired / Pemusnahan",
                "document_number": expired_doc.document_number,
                "document_url": reverse("expired:expired_detail", args=[expired_doc.pk]),
                "item_code": expired_item.item.kode_barang,
                "item_name": expired_item.item.nama_barang,
                "item_display": _build_item_display(expired_item.item),
                "batch_lot": stock.batch_lot if stock else "-",
                "expiry_date": stock.expiry_date if stock else None,
                "quantity": expired_item.quantity,
                "unit_name": (
                    expired_item.item.satuan.name if expired_item.item.satuan else "-"
                ),
                "location_name": stock.location.name if stock and stock.location else "-",
                "facility_name": "-",
                "funding_source_name": (
                    stock.sumber_dana.name if stock and stock.sumber_dana else "-"
                ),
                "responsible_user": _display_user(responsible_user),
                "event_timestamp": event_timestamp,
                "event_date": event_timestamp.date() if event_timestamp else None,
                "notes": expired_item.notes or expired_doc.notes or "-",
                "reference_identifier": expired_item.pk,
                "reference_label": f"EXPITEM-{expired_item.pk}",
            }
        )

    return rows


def _build_distribution_transaction_map(distribution_ids):
    if not distribution_ids:
        return {}

    transactions = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.OUT,
            reference_type=Transaction.ReferenceType.DISTRIBUTION,
            reference_id__in=distribution_ids,
        )
        .select_related("location", "user")
        .order_by("created_at", "id")
    )

    transaction_map = defaultdict(list)
    for transaction in transactions:
        key = (
            transaction.reference_id,
            transaction.item_id,
            transaction.batch_lot,
            _normalize_quantity(transaction.quantity),
        )
        transaction_map[key].append(transaction)
    return transaction_map


def _pop_distribution_transaction(transaction_map, distribution_id, item_id, batch_lot, quantity):
    key = (distribution_id, item_id, batch_lot, _normalize_quantity(quantity))
    if transaction_map.get(key):
        return transaction_map[key].pop(0)
    return None


def _build_summary(rows):
    zero = Decimal("0")
    outcome_totals = {
        ExpiredAuditReportForm.OutcomeType.OUT: zero,
        ExpiredAuditReportForm.OutcomeType.DESTROY: zero,
    }
    item_totals = defaultdict(
        lambda: {
            "item_code": "",
            "item_name": "",
            "out_quantity": zero,
            "destroy_quantity": zero,
            "total_quantity": zero,
        }
    )

    for row in rows:
        outcome_totals[row["outcome_type"]] += row["quantity"]
        item_key = (row["item_code"], row["item_name"])
        item_summary = item_totals[item_key]
        item_summary["item_code"] = row["item_code"]
        item_summary["item_name"] = row["item_name"]
        item_summary["total_quantity"] += row["quantity"]
        if row["outcome_type"] == ExpiredAuditReportForm.OutcomeType.OUT:
            item_summary["out_quantity"] += row["quantity"]
        else:
            item_summary["destroy_quantity"] += row["quantity"]

    summary_by_outcome = [
        {
            "outcome_type": ExpiredAuditReportForm.OutcomeType.OUT,
            "label": "OUT (Distribusi)",
            "quantity": outcome_totals[ExpiredAuditReportForm.OutcomeType.OUT],
        },
        {
            "outcome_type": ExpiredAuditReportForm.OutcomeType.DESTROY,
            "label": "Destroy (Kedaluwarsa)",
            "quantity": outcome_totals[ExpiredAuditReportForm.OutcomeType.DESTROY],
        },
    ]

    summary_by_item = sorted(item_totals.values(), key=itemgetter("item_name", "item_code"))

    reconciliation_rows = []
    for row in summary_by_item:
        difference = row["out_quantity"] - row["destroy_quantity"]
        reconciliation_rows.append(
            {
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "out_quantity": row["out_quantity"],
                "destroy_quantity": row["destroy_quantity"],
                "difference": difference,
                "status": "SEIMBANG" if difference == 0 else "SELISIH",
            }
        )

    return {
        "summary_by_outcome": summary_by_outcome,
        "summary_by_item": summary_by_item,
        "reconciliation_rows": reconciliation_rows,
    }


def _build_item_display(item):
    code = item.kode_barang or "-"
    return f"{code} — {item.nama_barang}"


def _display_user(user):
    if not user:
        return "-"
    return user.get_full_name() or user.username


def _normalize_quantity(quantity):
    return Decimal(quantity).quantize(Decimal("0.01"))


def _resolve_location(stock, transaction):
    if stock:
        return stock.location
    if transaction:
        return transaction.location
    return None


def _resolve_responsible_user(transaction, distribution):
    if transaction:
        return transaction.user
    return distribution.approved_by


def _resolve_event_timestamp(transaction, distribution):
    if transaction:
        return transaction.created_at
    return distribution.approved_at
