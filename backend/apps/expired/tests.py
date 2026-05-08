from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.distribution.models import Distribution
from apps.expired.forms import ExpiredItemForm
from apps.expired.models import Expired, ExpiredItem
from apps.expired.services import generate_expired_audit_report
from apps.items.models import (
    Category,
    Facility,
    FundingSource,
    Item,
    Location,
    Unit,
)
from apps.stock.models import Stock, Transaction
from apps.users.access import ensure_default_module_access
from apps.users.models import User


class ExpiredWorkflowTest(TestCase):
    """Tests for the expired module workflow transitions, stock posting, and edge cases."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="gudang_expired",
            password="secret12345",
        )

        self.unit = Unit.objects.create(code="BOT", name="Botol")
        self.category = Category.objects.create(
            code="SYRUP", name="Sirup", sort_order=1
        )
        self.item = Item.objects.create(
            nama_barang="Sirup Cough 60ml",
            satuan=self.unit,
            kategori=self.category,
            minimum_stock=Decimal("0"),
        )
        self.location = Location.objects.create(code="LOC-02", name="Gudang Farmasi")
        self.funding_source = FundingSource.objects.create(
            code="APBD", name="Anggaran APBD"
        )
        self.other_funding_source = FundingSource.objects.create(
            code="BOK", name="Dana BOK"
        )
        self.facility = Facility.objects.create(
            code="PKM-01", name="Puskesmas Audit"
        )

        self.stock = Stock.objects.create(
            item=self.item,
            location=self.location,
            batch_lot="BATCH-EXP-01",
            expiry_date="2026-01-01",
            quantity=Decimal("50"),
            reserved=Decimal("0"),
            unit_price=Decimal("2500"),
            sumber_dana=self.funding_source,
        )

        self.client.force_login(self.user)

    def _create_expired(
        self, status=Expired.Status.DRAFT, with_items=True, document_number=""
    ):
        """Helper to create an expired document with optional items."""
        kwargs = {
            "report_date": "2026-03-10",
            "status": status,
            "created_by": self.user,
        }
        if document_number:
            kwargs["document_number"] = document_number
        expired_doc = Expired.objects.create(**kwargs)
        if with_items:
            ExpiredItem.objects.create(
                expired=expired_doc,
                item=self.item,
                stock=self.stock,
                quantity=Decimal("5"),
                notes="Melewati tanggal ED",
            )
        return expired_doc

    def _create_distributed_outcome(
        self,
        *,
        quantity=Decimal("4"),
        distributed_date="2026-03-12",
        funding_source=None,
        item=None,
    ):
        funding_source = funding_source or self.funding_source
        item = item or self.item
        stock = Stock.objects.create(
            item=item,
            location=self.location,
            batch_lot=f"BATCH-OUT-{Stock.objects.count()}",
            expiry_date="2026-01-15",
            quantity=Decimal("20"),
            reserved=Decimal("0"),
            unit_price=Decimal("3000"),
            sumber_dana=funding_source,
        )
        distribution = Distribution.objects.create(
            distribution_type=Distribution.DistributionType.SPECIAL_REQUEST,
            request_date=distributed_date,
            facility=self.facility,
            status=Distribution.Status.DISTRIBUTED,
            created_by=self.user,
            approved_by=self.user,
            approved_at=timezone.make_aware(datetime(2026, 3, 12, 9, 0, 0)),
            distributed_date=distributed_date,
            notes="Distribusi batch ED",
        )
        distribution_item = distribution.items.create(
            item=item,
            quantity_requested=quantity,
            quantity_approved=quantity,
            stock=stock,
            issued_batch_lot=stock.batch_lot,
            issued_expiry_date=stock.expiry_date,
            issued_unit_price=stock.unit_price,
            issued_sumber_dana=funding_source,
            notes="Dikeluarkan untuk kebutuhan khusus",
        )
        transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.OUT,
            item=item,
            location=self.location,
            batch_lot=stock.batch_lot,
            quantity=quantity,
            unit_price=stock.unit_price,
            sumber_dana=funding_source,
            reference_type=Transaction.ReferenceType.DISTRIBUTION,
            reference_id=distribution.id,
            user=self.user,
            notes="Distribusi audit",
        )
        transaction_timestamp = timezone.make_aware(datetime(2026, 3, 12, 9, 30, 0))
        Transaction.objects.filter(pk=transaction.pk).update(created_at=transaction_timestamp)
        transaction.refresh_from_db()
        return distribution, distribution_item, transaction

    # --- Auto-generated document number ---

    def test_auto_generated_document_number(self):
        expired_doc = self._create_expired()
        self.assertTrue(expired_doc.document_number.startswith("EXP-"))
        now_prefix = timezone.now().strftime("%Y%m")
        self.assertIn(now_prefix, expired_doc.document_number)

    def test_custom_document_number_preserved(self):
        expired_doc = self._create_expired(document_number="CUSTOM-EXP-001")
        self.assertEqual(expired_doc.document_number, "CUSTOM-EXP-001")

    # --- Submit workflow ---

    def test_submit_draft_to_submitted(self):
        expired_doc = self._create_expired(status=Expired.Status.DRAFT)
        response = self.client.post(
            reverse("expired:expired_submit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.SUBMITTED)

    def test_submit_requires_items(self):
        expired_doc = self._create_expired(
            status=Expired.Status.DRAFT, with_items=False
        )
        response = self.client.post(
            reverse("expired:expired_submit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.DRAFT)  # unchanged

    def test_submit_only_from_draft(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_submit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.SUBMITTED)  # unchanged

    # --- Verify workflow (stock deduction + transaction) ---

    def test_verify_deducts_stock_and_creates_transaction(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_verify", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)

        expired_doc.refresh_from_db()
        self.stock.refresh_from_db()

        self.assertEqual(expired_doc.status, Expired.Status.VERIFIED)
        self.assertEqual(expired_doc.verified_by, self.user)
        self.assertIsNotNone(expired_doc.verified_at)
        self.assertEqual(self.stock.quantity, Decimal("45"))  # 50 - 5

        txn = Transaction.objects.get(
            reference_type=Transaction.ReferenceType.EXPIRED,
            reference_id=expired_doc.id,
        )
        self.assertEqual(txn.transaction_type, Transaction.TransactionType.OUT)
        self.assertEqual(txn.quantity, Decimal("5"))
        self.assertEqual(txn.item, self.item)

    def test_verify_insufficient_stock_fails(self):
        self.stock.quantity = Decimal("3")
        self.stock.save()
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_verify", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.SUBMITTED)  # unchanged
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal("3"))  # unchanged

    def test_verify_only_from_submitted(self):
        expired_doc = self._create_expired(status=Expired.Status.DRAFT)
        response = self.client.post(
            reverse("expired:expired_verify", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.DRAFT)  # unchanged

    # --- Dispose workflow ---

    def test_dispose_verified_to_disposed(self):
        expired_doc = self._create_expired(status=Expired.Status.VERIFIED)
        expired_doc.verified_by = self.user
        expired_doc.verified_at = timezone.now()
        expired_doc.save()

        response = self.client.post(
            reverse("expired:expired_dispose", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.DISPOSED)
        self.assertEqual(expired_doc.disposed_by, self.user)
        self.assertIsNotNone(expired_doc.disposed_at)

    def test_dispose_only_from_verified(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_dispose", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.SUBMITTED)  # unchanged

    def test_reset_to_draft_from_submitted(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_reset_to_draft", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.DRAFT)

    def test_reset_to_draft_blocked_for_verified(self):
        expired_doc = self._create_expired(status=Expired.Status.VERIFIED)
        response = self.client.post(
            reverse("expired:expired_reset_to_draft", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.VERIFIED)

    def test_step_back_disposed_to_verified(self):
        expired_doc = self._create_expired(status=Expired.Status.DISPOSED)
        expired_doc.disposed_by = self.user
        expired_doc.disposed_at = timezone.now()
        expired_doc.save(update_fields=["disposed_by", "disposed_at", "updated_at"])

        response = self.client.post(
            reverse("expired:expired_step_back", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.VERIFIED)
        self.assertIsNone(expired_doc.disposed_by)
        self.assertIsNone(expired_doc.disposed_at)

    def test_step_back_blocked_for_verified(self):
        expired_doc = self._create_expired(status=Expired.Status.VERIFIED)
        response = self.client.post(
            reverse("expired:expired_step_back", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        expired_doc.refresh_from_db()
        self.assertEqual(expired_doc.status, Expired.Status.VERIFIED)

    # --- Edit access ---

    def test_edit_allowed_for_draft(self):
        expired_doc = self._create_expired(status=Expired.Status.DRAFT)
        response = self.client.get(
            reverse("expired:expired_edit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_allowed_for_submitted(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.get(
            reverse("expired:expired_edit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_blocked_for_verified(self):
        expired_doc = self._create_expired(status=Expired.Status.VERIFIED)
        response = self.client.get(
            reverse("expired:expired_edit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)  # redirect with error

    def test_edit_blocked_for_disposed(self):
        expired_doc = self._create_expired(status=Expired.Status.DISPOSED)
        response = self.client.get(
            reverse("expired:expired_edit", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)  # redirect with error

    # --- Delete ---

    def test_delete_draft_expired(self):
        expired_doc = self._create_expired(status=Expired.Status.DRAFT)
        pk = expired_doc.pk
        response = self.client.post(reverse("expired:expired_delete", args=[pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expired.objects.filter(pk=pk).exists())

    def test_delete_blocked_for_submitted(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        response = self.client.post(
            reverse("expired:expired_delete", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Expired.objects.filter(pk=expired_doc.pk).exists()
        )  # still exists

    def test_gudang_cannot_verify_expired(self):
        expired_doc = self._create_expired(status=Expired.Status.SUBMITTED)
        gudang = User.objects.create_user(
            username="gudang_only_exp",
            password="secret12345",
            role=User.Role.GUDANG,
        )
        ensure_default_module_access(gudang, overwrite=True)
        self.client.force_login(gudang)

        response = self.client.post(
            reverse("expired:expired_verify", args=[expired_doc.pk])
        )
        self.assertEqual(response.status_code, 403)

    # --- Pending quantity handling ---

    def test_expired_create_prefills_only_remaining_quantity_after_submitted_docs(self):
        self._create_expired(status=Expired.Status.SUBMITTED)

        response = self.client.get(
            reverse("expired:expired_create") + f"?stocks={self.stock.pk}"
        )

        self.assertEqual(response.status_code, 200)
        formset = response.context["formset"]
        self.assertEqual(formset.forms[0].initial["quantity"], Decimal("45"))

    def test_expired_create_prefills_one_form_per_selected_stock(self):
        other_item = Item.objects.create(
            nama_barang="Paracetamol 500mg",
            satuan=self.unit,
            kategori=self.category,
            minimum_stock=Decimal("0"),
        )
        third_item = Item.objects.create(
            nama_barang="Vitamin C 100mg",
            satuan=self.unit,
            kategori=self.category,
            minimum_stock=Decimal("0"),
        )
        other_stock = Stock.objects.create(
            item=other_item,
            location=self.location,
            batch_lot="BATCH-EXP-02",
            expiry_date="2026-02-01",
            quantity=Decimal("25"),
            reserved=Decimal("0"),
            unit_price=Decimal("1500"),
            sumber_dana=self.funding_source,
        )
        third_stock = Stock.objects.create(
            item=third_item,
            location=self.location,
            batch_lot="BATCH-EXP-03",
            expiry_date="2026-03-01",
            quantity=Decimal("10"),
            reserved=Decimal("0"),
            unit_price=Decimal("500"),
            sumber_dana=self.funding_source,
        )

        response = self.client.get(
            reverse("expired:expired_create")
            + f"?stocks={self.stock.pk},{other_stock.pk},{third_stock.pk}"
        )

        self.assertEqual(response.status_code, 200)
        formset = response.context["formset"]
        self.assertEqual(formset.total_form_count(), 3)
        self.assertEqual(len(formset.forms), 3)

        initial_by_stock = {
            form.initial["stock"]: {
                "item": form.initial["item"],
                "quantity": form.initial["quantity"],
            }
            for form in formset.forms
        }
        self.assertEqual(
            initial_by_stock,
            {
                self.stock.pk: {
                    "item": self.item.pk,
                    "quantity": Decimal("50"),
                },
                other_stock.pk: {
                    "item": other_item.pk,
                    "quantity": Decimal("25"),
                },
                third_stock.pk: {
                    "item": third_item.pk,
                    "quantity": Decimal("10"),
                },
            },
        )

    def test_expired_create_rejects_quantity_reserved_by_other_submitted_docs(self):
        self._create_expired(status=Expired.Status.SUBMITTED)

        response = self.client.post(
            reverse("expired:expired_create"),
            {
                "document_number": "",
                "report_date": "2026-03-15",
                "notes": "Dokumen baru",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": str(self.item.pk),
                "items-0-stock": str(self.stock.pk),
                "items-0-quantity": "46",
                "items-0-notes": "Perlu diproses",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expired.objects.count(), 1)
        error_message = response.context["formset"].forms[0].errors["quantity"][0]
        self.assertIn(
            "Jumlah melebihi stok yang masih bisa diproses.", error_message
        )
        self.assertIn(
            "dokumen kedaluwarsa yang masih diajukan sebanyak", error_message
        )

    def test_expired_item_form_uses_picker_label_without_suffixes(self):
        self.item.nama_barang = "Sirup Cough 60ml [P]"
        self.item.save(update_fields=["nama_barang", "updated_at"])

        form = ExpiredItemForm()

        self.assertEqual(form.fields["item"].label_from_instance(self.item), "Sirup Cough 60ml")

    def test_expired_create_includes_item_picker_table_script(self):
        response = self.client.get(reverse("expired:expired_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "js/item-picker-table.js?v=")

    def test_expired_alerts_show_remaining_actionable_quantity(self):
        self._create_expired(status=Expired.Status.SUBMITTED)

        response = self.client.get(reverse("expired:expired_alerts") + "?pending=0")

        self.assertEqual(response.status_code, 200)
        row = response.context["items"].object_list[0]
        self.assertEqual(row["pending_quantity"], Decimal("5"))
        self.assertEqual(row["actionable"], Decimal("45"))

    def test_expired_alerts_hide_fully_allocated_batch_when_pending_only(self):
        expired_doc = Expired.objects.create(
            report_date="2026-03-10",
            status=Expired.Status.SUBMITTED,
            created_by=self.user,
        )
        ExpiredItem.objects.create(
            expired=expired_doc,
            item=self.item,
            stock=self.stock,
            quantity=Decimal("50"),
            notes="Menunggu verifikasi",
        )

        response = self.client.get(reverse("expired:expired_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["items"].object_list), [])

    def test_expired_list_shows_audit_report_action(self):
        response = self.client.get(reverse("expired:expired_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generate Expired Audit Report")

    def test_generate_expired_audit_report_combines_distribution_and_destroy_rows(self):
        distribution, _, transaction = self._create_distributed_outcome()
        expired_doc = self._create_expired(status=Expired.Status.DISPOSED)
        expired_doc.verified_by = self.user
        expired_doc.verified_at = timezone.make_aware(datetime(2026, 3, 10, 8, 0, 0))
        expired_doc.disposed_by = self.user
        expired_doc.disposed_at = timezone.make_aware(datetime(2026, 3, 15, 10, 30, 0))
        expired_doc.save(
            update_fields=[
                "verified_by",
                "verified_at",
                "disposed_by",
                "disposed_at",
                "updated_at",
            ]
        )

        report = generate_expired_audit_report(
            {
                "start_date": datetime(2026, 3, 1).date(),
                "end_date": datetime(2026, 3, 31).date(),
                "location": None,
                "facility": None,
                "item": None,
                "outcome_type": "BOTH",
                "funding_source": None,
            }
        )

        self.assertEqual(len(report["rows"]), 2)
        self.assertEqual(report["rows"][0]["document_number"], distribution.document_number)
        self.assertEqual(report["rows"][0]["reference_identifier"], transaction.id)
        self.assertEqual(report["rows"][1]["document_number"], expired_doc.document_number)
        self.assertEqual(report["summary_by_outcome"][0]["quantity"], Decimal("4"))
        self.assertEqual(report["summary_by_outcome"][1]["quantity"], Decimal("5"))

    def test_expired_audit_report_filters_by_outcome_and_funding_source(self):
        self._create_distributed_outcome(funding_source=self.other_funding_source)
        self._create_distributed_outcome(funding_source=self.funding_source)

        response = self.client.get(
            reverse("expired:expired_audit_report"),
            {
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "outcome_type": "OUT",
                "funding_source": self.other_funding_source.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        rows = response.context["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["funding_source_name"], self.other_funding_source.name)
        self.assertEqual(rows[0]["outcome_type"], "OUT")

    def test_expired_audit_report_csv_export_returns_download(self):
        distribution, _, _ = self._create_distributed_outcome()

        response = self.client.get(
            reverse("expired:expired_audit_report"),
            {
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "format": "csv",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("expired_audit_report_2026-03-01_2026-03-31.csv", response["Content-Disposition"])
        self.assertIn(distribution.document_number, response.content.decode("utf-8"))
        self.assertIn("SUMMARY_OUTCOME", response.content.decode("utf-8"))

    def test_expired_audit_report_pdf_export_returns_pdf(self):
        self._create_distributed_outcome()

        response = self.client.get(
            reverse("expired:expired_audit_report"),
            {
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "format": "pdf",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("expired_audit_report_2026-03-01_2026-03-31.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
