from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.items.models import Category, FundingSource, Item, Location, Unit
from apps.receiving.admin import ReceivingAdmin
from apps.receiving.models import Receiving, ReceivingItem
from apps.stock.models import Stock, Transaction
from apps.users.models import User


class ReceivingCSVImportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin_receiving",
            password="secret12345",
        )

        unit = Unit.objects.create(code="TAB", name="Tablet")
        category = Category.objects.create(code="OBAT", name="Obat", sort_order=1)
        self.item = Item.objects.create(
            kode_barang="ITM-TEST-0001",
            nama_barang="Paracetamol 500mg",
            satuan=unit,
            kategori=category,
            minimum_stock=Decimal("0"),
        )
        self.funding = FundingSource.objects.create(code="APBD", name="APBD")
        self.location = Location.objects.create(code="GUDANG", name="Gudang Utama")

        self.admin = ReceivingAdmin(Receiving, AdminSite())

    @staticmethod
    def _csv_file(content):
        return SimpleUploadedFile(
            "receiving.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_process_csv_applies_defaults_for_empty_optional_fields(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,ITM-TEST-0001,,,,\n"
        )

        result = self.admin._process_csv(self._csv_file(csv_content), self.user)

        self.assertEqual(result["receivings"], 1)
        self.assertEqual(result["items"], 1)
        self.assertEqual(result["stock"], 1)
        self.assertEqual(result["transactions"], 1)

        receiving_item = ReceivingItem.objects.get()
        self.assertEqual(receiving_item.quantity, Decimal("0"))
        self.assertEqual(receiving_item.unit_price, Decimal("0"))
        self.assertEqual(receiving_item.batch_lot, "SALDO-0002")
        self.assertEqual(receiving_item.expiry_date, date(2099, 12, 31))

        stock = Stock.objects.get()
        self.assertEqual(stock.quantity, Decimal("0"))
        self.assertEqual(stock.batch_lot, "SALDO-0002")

    def test_process_csv_handles_missing_cell_without_strip_crash(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,,10,B-001,01/01/2030,1000\n"
        )

        with self.assertRaisesMessage(ValueError, "Baris 2: item_code kosong"):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

    def test_process_csv_invalid_foreign_key_has_clear_message(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,ITM-NOT-FOUND,10,B-001,01/01/2030,1000\n"
        )

        with self.assertRaisesMessage(
            ValueError, "Baris 2: item_code 'ITM-NOT-FOUND' tidak ditemukan"
        ):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

    def test_process_csv_invalid_decimal_has_clear_message(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,ITM-TEST-0001,sepuluh,B-001,01/01/2030,1000\n"
        )

        with self.assertRaisesMessage(
            ValueError, "Baris 2: format quantity tidak valid: 'sepuluh'"
        ):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

    def test_process_csv_missing_required_header_rejected(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,10,B-001,01/01/2030,1000\n"
        )

        with self.assertRaisesMessage(
            ValueError, "Kolom wajib tidak ditemukan: item_code"
        ):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

    def test_process_csv_invalid_date_has_clear_message(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,notadate,,APBD,GUDANG,ITM-TEST-0001,10,B-001,01/01/2030,1000\n"
        )

        with self.assertRaisesMessage(
            ValueError,
            "Baris 2: format receiving_date tidak dikenali: 'notadate'. Gunakan DD/MM/YYYY.",
        ):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

    def test_process_csv_rolls_back_on_error(self):
        csv_content = (
            "document_number,receiving_type,receiving_date,supplier_code,sumber_dana_code,"
            "location_code,item_code,quantity,batch_lot,expiry_date,unit_price\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,ITM-TEST-0001,10,B-001,01/01/2030,1000\n"
            "RCV-2026-00001,GRANT,12/03/2026,,APBD,GUDANG,ITM-NOT-FOUND,10,B-002,01/01/2030,1000\n"
        )

        with self.assertRaises(ValueError):
            self.admin._process_csv(self._csv_file(csv_content), self.user)

        self.assertEqual(Receiving.objects.count(), 0)
        self.assertEqual(ReceivingItem.objects.count(), 0)
        self.assertEqual(Stock.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)
