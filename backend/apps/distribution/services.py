from django.db import transaction
from django.utils import timezone

from apps.stock.models import Stock, Transaction

from .models import Distribution, DistributionStaffAssignment


class DistributionWorkflowError(ValueError):
    pass


def _get_distribution_items(distribution, action_label):
    distribution_items = list(distribution.items.select_related("item", "stock"))
    if not distribution_items:
        raise DistributionWorkflowError(
            f"Distribusi tidak memiliki item untuk {action_label}."
        )
    return distribution_items


def _validate_distribution_item_for_stock_workflow(distribution_item, action_label):
    if distribution_item.quantity_approved is None or distribution_item.quantity_approved <= 0:
        raise DistributionWorkflowError(
            f"Item {distribution_item.item.nama_barang}: jumlah disetujui harus diisi dan lebih dari 0."
        )

    if distribution_item.stock is None:
        raise DistributionWorkflowError(
            f"Item {distribution_item.item.nama_barang}: batch stok harus dipilih sebelum {action_label}."
        )

    if distribution_item.quantity_approved > distribution_item.stock.available_quantity:
        raise DistributionWorkflowError(
            f"Stok tidak cukup untuk {distribution_item.item.nama_barang}. "
            f"Tersedia {distribution_item.stock.available_quantity}, disetujui {distribution_item.quantity_approved}."
        )


def assign_default_distribution_staff(distribution, user):
    if distribution is None or user is None:
        return

    DistributionStaffAssignment.objects.get_or_create(
        distribution=distribution,
        user=user,
    )


def execute_distribution_verification(distribution, user):
    distribution_items = _get_distribution_items(distribution, "diverifikasi")

    for distribution_item in distribution_items:
        _validate_distribution_item_for_stock_workflow(
            distribution_item,
            "verifikasi",
        )

    distribution.status = Distribution.Status.VERIFIED
    distribution.verified_by = user
    distribution.verified_at = timezone.now()
    distribution.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])


def execute_stock_distribution(distribution, user):
    distribution_items = _get_distribution_items(distribution, "didistribusikan")

    processed_at = timezone.now()

    with transaction.atomic():
        for distribution_item in distribution_items:
            _validate_distribution_item_for_stock_workflow(
                distribution_item,
                "distribusi",
            )

            quantity = distribution_item.quantity_approved

            stock = Stock.objects.select_for_update().get(pk=distribution_item.stock_id)

            if stock.item_id != distribution_item.item_id:
                raise DistributionWorkflowError(
                    f"Batch stok tidak sesuai untuk item {distribution_item.item.nama_barang}."
                )

            if quantity > stock.available_quantity:
                raise DistributionWorkflowError(
                    f"Stok tidak cukup untuk {distribution_item.item.nama_barang}. "
                    f"Tersedia {stock.available_quantity}, disetujui {quantity}."
                )

            stock.quantity = stock.quantity - quantity
            stock.save(update_fields=["quantity", "updated_at"])

            Transaction.objects.create(
                transaction_type=Transaction.TransactionType.OUT,
                item=distribution_item.item,
                location=stock.location,
                batch_lot=stock.batch_lot,
                quantity=quantity,
                unit_price=stock.unit_price,
                sumber_dana=stock.sumber_dana,
                reference_type=Transaction.ReferenceType.DISTRIBUTION,
                reference_id=distribution.id,
                user=user,
                notes=(
                    f"Distribusi {distribution.document_number} ke {distribution.facility}: "
                    f"{distribution_item.notes}"
                ).strip(),
            )

        distribution.status = Distribution.Status.DISTRIBUTED
        distribution.approved_by = user
        distribution.approved_at = processed_at
        distribution.distributed_date = processed_at.date()
        distribution.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "distributed_date",
                "updated_at",
            ]
        )