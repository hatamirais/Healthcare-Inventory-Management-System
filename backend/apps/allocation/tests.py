from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.allocation.models import (
    Allocation,
    AllocationFacility,
    AllocationItem,
    AllocationStaffAssignment,
)
from apps.items.models import Category, Facility, FundingSource, Item, Location, Unit
from apps.stock.models import Stock, Transaction
from apps.users.access import ensure_default_module_access
from apps.users.models import ModuleAccess, User


@override_settings(FEATURE_ALLOCATION_UI_ENABLED=True)
class AllocationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="allocation_admin",
            password="secret12345",
        )
        cls.staff = User.objects.create_user(
            username="allocation_staff",
            password="secret12345",
            full_name="Petugas Alokasi",
        )
        ensure_default_module_access(cls.staff)

        cls.unit = Unit.objects.create(code="TAB", name="Tablet")
        cls.category = Category.objects.create(code="OBT", name="Obat", sort_order=1)
        cls.item = Item.objects.create(
            nama_barang="Paracetamol 500mg",
            satuan=cls.unit,
            kategori=cls.category,
            minimum_stock=Decimal("0"),
        )
        cls.location = Location.objects.create(code="LOC-ALC", name="Gudang Alokasi")
        cls.funding_source = FundingSource.objects.create(code="APBD", name="APBD")
        cls.facility = Facility.objects.create(code="PKM-A", name="Puskesmas A")
        cls.other_facility = Facility.objects.create(code="PKM-B", name="Puskesmas B")
        cls.stock = Stock.objects.create(
            item=cls.item,
            location=cls.location,
            batch_lot="ALC-01",
            expiry_date="2027-12-31",
            quantity=Decimal("100"),
            reserved=Decimal("0"),
            unit_price=Decimal("2500"),
            sumber_dana=cls.funding_source,
        )

    def _create_allocation(self, document_number=""):
        return Allocation.objects.create(
            document_number=document_number,
            allocation_date="2026-04-20",
            created_by=self.user,
        )

    def test_auto_generates_document_number_when_blank(self):
        allocation = self._create_allocation(document_number="")
        self.assertTrue(allocation.document_number.startswith("ALC-"))
        self.assertEqual(len(allocation.document_number), 16)

    def test_keeps_manual_document_number_when_provided(self):
        allocation = self._create_allocation(document_number="ALC-MANUAL-001")
        self.assertEqual(allocation.document_number, "ALC-MANUAL-001")

    def test_allocation_item_requires_facility_selected_on_header(self):
        allocation = self._create_allocation()
        item = AllocationItem(
            allocation=allocation,
            facility=self.facility,
            item=self.item,
            quantity=Decimal("5"),
            stock=self.stock,
        )

        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()

        self.assertIn("facility", ctx.exception.message_dict)

    def test_allocation_item_accepts_selected_header_facility(self):
        allocation = self._create_allocation()
        AllocationFacility.objects.create(allocation=allocation, facility=self.facility)

        item = AllocationItem(
            allocation=allocation,
            facility=self.facility,
            item=self.item,
            quantity=Decimal("5"),
            stock=self.stock,
        )

        item.full_clean()

    def test_allocation_item_rejects_stock_from_different_item(self):
        allocation = self._create_allocation()
        AllocationFacility.objects.create(allocation=allocation, facility=self.facility)
        other_item = Item.objects.create(
            nama_barang="Amoxicillin",
            satuan=self.unit,
            kategori=self.category,
            minimum_stock=Decimal("0"),
        )

        item = AllocationItem(
            allocation=allocation,
            facility=self.facility,
            item=other_item,
            quantity=Decimal("5"),
            stock=self.stock,
        )

        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()

        self.assertIn("stock", ctx.exception.message_dict)

    def test_allocation_item_rejects_quantity_above_available_stock(self):
        allocation = self._create_allocation()
        AllocationFacility.objects.create(allocation=allocation, facility=self.facility)
        item = AllocationItem(
            allocation=allocation,
            facility=self.facility,
            item=self.item,
            quantity=Decimal("150"),
            stock=self.stock,
        )

        with self.assertRaises(ValidationError) as ctx:
            item.full_clean()

        self.assertIn("quantity", ctx.exception.message_dict)

    def test_allocation_staff_assignment_is_unique_per_user(self):
        allocation = self._create_allocation()
        AllocationStaffAssignment.objects.create(allocation=allocation, user=self.staff)

        with self.assertRaises(Exception):
            AllocationStaffAssignment.objects.create(
                allocation=allocation,
                user=self.staff,
            )


@override_settings(FEATURE_ALLOCATION_UI_ENABLED=True)
class AllocationRouteTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="allocation_operator",
            password="secret12345",
            role=User.Role.ADMIN_UMUM,
            full_name="Operator Alokasi",
        )
        ensure_default_module_access(cls.user)
        cls.blocked_user = User.objects.create_user(
            username="allocation_blocked",
            password="secret12345",
            role=User.Role.PUSKESMAS,
        )
        ensure_default_module_access(cls.blocked_user)

        cls.allocation = Allocation.objects.create(
            allocation_date="2026-04-20",
            created_by=cls.user,
        )

    def test_allocation_list_available_for_operator(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("allocation:allocation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daftar Alokasi")
        self.assertContains(response, reverse("allocation:allocation_list"))

    def test_allocation_detail_available_for_operator(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("allocation:allocation_detail", args=[self.allocation.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.allocation.document_number)

    def test_allocation_list_forbidden_without_scope(self):
        self.client.force_login(self.blocked_user)

        response = self.client.get(reverse("allocation:allocation_list"))

        self.assertEqual(response.status_code, 403)

    def test_allocation_create_saves_staff_facilities_and_items(self):
        self.client.force_login(self.user)
        unit = Unit.objects.create(code="BOT", name="Botol")
        category = Category.objects.create(code="ALK", name="Alkes", sort_order=2)
        item = Item.objects.create(
            nama_barang="Vitamin Syrup",
            satuan=unit,
            kategori=category,
            minimum_stock=Decimal("0"),
        )
        location = Location.objects.create(code="LOC-CRT", name="Gudang Create")
        funding_source = FundingSource.objects.create(code="BOK", name="BOK")
        stock = Stock.objects.create(
            item=item,
            location=location,
            batch_lot="CRT-01",
            expiry_date="2027-10-31",
            quantity=Decimal("20"),
            reserved=Decimal("0"),
            unit_price=Decimal("5000"),
            sumber_dana=funding_source,
        )
        facility_a = Facility.objects.create(code="PKM-C", name="Puskesmas C")
        facility_b = Facility.objects.create(code="PKM-D", name="Puskesmas D")
        staff = User.objects.create_user(
            username="allocation_staff_2",
            password="secret12345",
            full_name="Petugas Dua",
        )
        ensure_default_module_access(staff)

        response = self.client.post(
            reverse("allocation:allocation_create"),
            {
                "document_number": "",
                "allocation_date": "2026-04-20",
                "notes": "Alokasi awal",
                "selected_facilities": [facility_a.pk, facility_b.pk],
                "assigned_staff": [self.user.pk, staff.pk],
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-facility": facility_a.pk,
                "items-0-item": item.pk,
                "items-0-quantity": "10",
                "items-0-stock": stock.pk,
                "items-0-notes": "Prioritas",
            },
        )

        self.assertEqual(response.status_code, 302)

        allocation = Allocation.objects.latest("id")
        self.assertTrue(allocation.document_number.startswith("ALC-"))
        self.assertEqual(allocation.selected_facilities.count(), 2)
        self.assertEqual(allocation.staff_assignments.count(), 2)
        self.assertEqual(allocation.items.count(), 1)
        self.assertEqual(allocation.items.first().facility, facility_a)

    def test_allocation_create_rejects_item_facility_outside_header_selection(self):
        self.client.force_login(self.user)
        unit = Unit.objects.create(code="PCS", name="Pieces")
        category = Category.objects.create(code="TES", name="Testing", sort_order=3)
        item = Item.objects.create(
            nama_barang="Masker",
            satuan=unit,
            kategori=category,
            minimum_stock=Decimal("0"),
        )
        location = Location.objects.create(code="LOC-ERR", name="Gudang Error")
        funding_source = FundingSource.objects.create(code="ERR", name="Error Fund")
        stock = Stock.objects.create(
            item=item,
            location=location,
            batch_lot="ERR-01",
            expiry_date="2027-12-31",
            quantity=Decimal("20"),
            reserved=Decimal("0"),
            unit_price=Decimal("1000"),
            sumber_dana=funding_source,
        )
        selected_facility = Facility.objects.create(code="PKM-E", name="Puskesmas E")
        outside_facility = Facility.objects.create(code="PKM-F", name="Puskesmas F")

        response = self.client.post(
            reverse("allocation:allocation_create"),
            {
                "document_number": "ALC-MANUAL-002",
                "allocation_date": "2026-04-20",
                "notes": "Alokasi error",
                "selected_facilities": [selected_facility.pk],
                "assigned_staff": [self.user.pk],
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-facility": outside_facility.pk,
                "items-0-item": item.pk,
                "items-0-quantity": "5",
                "items-0-stock": stock.pk,
                "items-0-notes": "Salah fasilitas",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fasilitas item harus dipilih pada header alokasi.")

    def test_allocation_edit_updates_staff_and_facilities(self):
        self.client.force_login(self.user)
        unit = Unit.objects.create(code="TAB2", name="Tablet 2")
        category = Category.objects.create(code="EDIT", name="Edit", sort_order=4)
        item = Item.objects.create(
            nama_barang="Zinc",
            satuan=unit,
            kategori=category,
            minimum_stock=Decimal("0"),
        )
        location = Location.objects.create(code="LOC-EDT", name="Gudang Edit")
        funding_source = FundingSource.objects.create(code="EDT", name="Edit Fund")
        stock = Stock.objects.create(
            item=item,
            location=location,
            batch_lot="EDT-01",
            expiry_date="2028-01-31",
            quantity=Decimal("30"),
            reserved=Decimal("0"),
            unit_price=Decimal("2000"),
            sumber_dana=funding_source,
        )
        facility_a = Facility.objects.create(code="PKM-G", name="Puskesmas G")
        facility_b = Facility.objects.create(code="PKM-H", name="Puskesmas H")
        facility_c = Facility.objects.create(code="PKM-I", name="Puskesmas I")
        staff_old = User.objects.create_user(
            username="allocation_staff_old",
            password="secret12345",
            full_name="Petugas Lama",
        )
        staff_new = User.objects.create_user(
            username="allocation_staff_new",
            password="secret12345",
            full_name="Petugas Baru",
        )
        ensure_default_module_access(staff_old)
        ensure_default_module_access(staff_new)

        allocation = Allocation.objects.create(
            document_number="ALC-MANUAL-EDIT",
            allocation_date="2026-04-20",
            created_by=self.user,
        )
        AllocationFacility.objects.create(allocation=allocation, facility=facility_a)
        allocation.staff_assignments.create(user=staff_old)
        allocation.items.create(
            facility=facility_a,
            item=item,
            quantity=Decimal("5"),
            stock=stock,
        )
        line = allocation.items.first()

        response = self.client.post(
            reverse("allocation:allocation_edit", args=[allocation.pk]),
            {
                "document_number": "ALC-MANUAL-EDIT",
                "allocation_date": "2026-04-21",
                "notes": "Direvisi",
                "selected_facilities": [facility_b.pk, facility_c.pk],
                "assigned_staff": [staff_new.pk],
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": line.pk,
                "items-0-facility": facility_b.pk,
                "items-0-item": item.pk,
                "items-0-quantity": "7",
                "items-0-stock": stock.pk,
                "items-0-notes": "Ubah tujuan",
            },
        )

        self.assertEqual(response.status_code, 302)

        allocation.refresh_from_db()
        self.assertEqual(
            set(allocation.selected_facilities.values_list("facility_id", flat=True)),
            {facility_b.pk, facility_c.pk},
        )
        self.assertEqual(
            list(allocation.staff_assignments.values_list("user_id", flat=True)),
            [staff_new.pk],
        )
        self.assertEqual(allocation.items.first().facility_id, facility_b.pk)


@override_settings(FEATURE_ALLOCATION_UI_ENABLED=True)
class AllocationWorkflowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(
            username="allocation_operator_flow",
            password="secret12345",
            role=User.Role.ADMIN_UMUM,
            full_name="Operator Flow",
        )
        ensure_default_module_access(cls.operator)

        cls.approver = User.objects.create_user(
            username="allocation_approver_flow",
            password="secret12345",
            role=User.Role.KEPALA,
            full_name="Kepala Instalasi",
        )
        ensure_default_module_access(cls.approver)

        cls.unit = Unit.objects.create(code="ALCWF", name="Unit Flow")
        cls.category = Category.objects.create(code="ALCWF", name="Kategori Flow", sort_order=10)
        cls.item = Item.objects.create(
            nama_barang="Item Alokasi Flow",
            satuan=cls.unit,
            kategori=cls.category,
            minimum_stock=Decimal("0"),
        )
        cls.location = Location.objects.create(code="LOC-WF", name="Gudang Workflow")
        cls.funding_source = FundingSource.objects.create(code="WF", name="Workflow Fund")
        cls.facility = Facility.objects.create(code="PKM-WF", name="Puskesmas Workflow")

    def _create_stock(self, quantity="25"):
        return Stock.objects.create(
            item=self.item,
            location=self.location,
            batch_lot=f"WF-{Stock.objects.count() + 1:02d}",
            expiry_date="2028-12-31",
            quantity=Decimal(quantity),
            reserved=Decimal("0"),
            unit_price=Decimal("1500"),
            sumber_dana=self.funding_source,
        )

    def _create_allocation(self, status=Allocation.Status.DRAFT, quantity="7"):
        stock = self._create_stock()
        allocation = Allocation.objects.create(
            allocation_date="2026-04-21",
            created_by=self.operator,
            status=status,
        )
        AllocationFacility.objects.create(allocation=allocation, facility=self.facility)
        AllocationStaffAssignment.objects.create(allocation=allocation, user=self.operator)
        AllocationItem.objects.create(
            allocation=allocation,
            facility=self.facility,
            item=self.item,
            quantity=Decimal(quantity),
            stock=stock,
            notes="Catatan workflow",
        )
        return allocation, stock

    def test_submit_marks_allocation_submitted_and_records_actor(self):
        allocation, _stock = self._create_allocation()
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse("allocation:allocation_submit", args=[allocation.pk])
        )

        self.assertEqual(response.status_code, 302)
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, Allocation.Status.SUBMITTED)
        self.assertEqual(allocation.submitted_by, self.operator)
        self.assertIsNotNone(allocation.submitted_at)

    def test_submit_requires_assigned_staff(self):
        allocation, _stock = self._create_allocation()
        allocation.staff_assignments.all().delete()
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse("allocation:allocation_submit", args=[allocation.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, Allocation.Status.DRAFT)
        self.assertContains(response, "Pilih minimal 1 petugas sebelum mengajukan alokasi.")

    def test_operator_cannot_approve_allocation(self):
        allocation, _stock = self._create_allocation(status=Allocation.Status.SUBMITTED)
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse("allocation:allocation_approve", args=[allocation.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_approve_prepare_and_distribute_updates_stock_and_transaction(self):
        allocation, stock = self._create_allocation(status=Allocation.Status.DRAFT)

        self.client.force_login(self.operator)
        self.client.post(reverse("allocation:allocation_submit", args=[allocation.pk]))

        self.client.force_login(self.approver)
        approve_response = self.client.post(
            reverse("allocation:allocation_approve", args=[allocation.pk])
        )

        self.assertEqual(approve_response.status_code, 302)
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, Allocation.Status.APPROVED)
        self.assertEqual(allocation.approved_by, self.approver)

        self.client.force_login(self.operator)
        prepare_response = self.client.post(
            reverse("allocation:allocation_prepare", args=[allocation.pk])
        )
        distribute_response = self.client.post(
            reverse("allocation:allocation_distribute", args=[allocation.pk])
        )

        self.assertEqual(prepare_response.status_code, 302)
        self.assertEqual(distribute_response.status_code, 302)

        allocation.refresh_from_db()
        stock.refresh_from_db()
        item_line = allocation.items.get()
        transaction = Transaction.objects.get(
            reference_type=Transaction.ReferenceType.ALLOCATION,
            reference_id=allocation.pk,
        )

        self.assertEqual(allocation.status, Allocation.Status.DISTRIBUTED)
        self.assertEqual(allocation.prepared_by, self.operator)
        self.assertEqual(allocation.distributed_by, self.operator)
        self.assertEqual(allocation.distributed_date.isoformat(), "2026-04-21")
        self.assertEqual(stock.quantity, Decimal("18"))
        self.assertEqual(item_line.issued_batch_lot, stock.batch_lot)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.OUT)
        self.assertEqual(transaction.quantity, Decimal("7"))
        self.assertIn(allocation.document_number, transaction.notes)

    def test_reset_to_draft_clears_workflow_metadata(self):
        allocation, _stock = self._create_allocation(status=Allocation.Status.REJECTED)
        allocation.submitted_by = self.operator
        allocation.approved_by = self.approver
        allocation.prepared_by = self.operator
        allocation.distributed_by = self.operator
        allocation.submitted_at = allocation.approved_at = allocation.prepared_at = allocation.distributed_at = allocation.updated_at
        allocation.distributed_date = allocation.allocation_date
        allocation.save(
            update_fields=[
                "submitted_by",
                "approved_by",
                "prepared_by",
                "distributed_by",
                "submitted_at",
                "approved_at",
                "prepared_at",
                "distributed_at",
                "distributed_date",
                "updated_at",
            ]
        )
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse("allocation:allocation_reset_to_draft", args=[allocation.pk])
        )

        self.assertEqual(response.status_code, 302)
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, Allocation.Status.DRAFT)
        self.assertIsNone(allocation.submitted_by)
        self.assertIsNone(allocation.approved_by)
        self.assertIsNone(allocation.prepared_by)
        self.assertIsNone(allocation.distributed_by)
        self.assertIsNone(allocation.distributed_date)

    def test_edit_is_blocked_after_submission(self):
        allocation, _stock = self._create_allocation(status=Allocation.Status.SUBMITTED)
        self.client.force_login(self.operator)

        response = self.client.get(
            reverse("allocation:allocation_edit", args=[allocation.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hanya alokasi Draft yang dapat diubah.")

    def test_delete_allows_rejected_only(self):
        allocation, _stock = self._create_allocation(status=Allocation.Status.REJECTED)
        self.client.force_login(self.operator)

        response = self.client.post(
            reverse("allocation:allocation_delete", args=[allocation.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Allocation.objects.filter(pk=allocation.pk).exists())


class AllocationDisabledRouteTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="allocation_hidden_user",
            password="secret12345",
            role=User.Role.ADMIN_UMUM,
        )
        ensure_default_module_access(cls.user)

    def test_allocation_list_redirects_to_dashboard_when_feature_disabled(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("allocation:allocation_list"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(
            response,
            "Modul Alokasi dinonaktifkan sementara sampai alur final ditetapkan.",
        )
