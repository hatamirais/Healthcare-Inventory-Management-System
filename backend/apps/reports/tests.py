from django.test import TestCase
from django.urls import reverse

from apps.distribution.models import Distribution
from apps.items.models import Category, Facility, FundingSource, Item, Location, Unit
from apps.stock.models import Stock
from apps.users.models import User


class NumberingHistoryReportTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.user = User.objects.create_superuser(
			username="reports-admin",
			password="secret12345",
		)
		cls.unit = Unit.objects.create(code="TAB", name="Tablet")
		cls.category = Category.objects.create(
			code="REPORT-CAT", name="Report Category", sort_order=1
		)
		cls.item = Item.objects.create(
			nama_barang="Paracetamol 500mg",
			satuan=cls.unit,
			kategori=cls.category,
		)
		cls.location = Location.objects.create(code="REP-LOC", name="Gudang Laporan")
		cls.funding_source = FundingSource.objects.create(code="BOK", name="BOK")
		cls.facility = Facility.objects.create(code="PKM-REP", name="Puskesmas Laporan")
		cls.stock = Stock.objects.create(
			item=cls.item,
			location=cls.location,
			batch_lot="REP-01",
			expiry_date="2027-12-31",
			quantity=10,
			reserved=0,
			unit_price=1000,
			sumber_dana=cls.funding_source,
		)

	def setUp(self):
		self.client.force_login(self.user)

	def _create_distribution(self, distribution_type, document_number=None):
		dist = Distribution.objects.create(
			distribution_type=distribution_type,
			document_number=document_number or "",
			request_date="2026-04-01",
			facility=self.facility,
			status=Distribution.Status.DRAFT,
			created_by=self.user,
			notes="Catatan ringkas",
		)
		dist.items.create(
			item=self.item,
			quantity_requested=5,
			quantity_approved=5,
			stock=self.stock,
		)
		return dist

	def test_numbering_history_page_lists_lplpo_and_special_request(self):
		lplpo_dist = self._create_distribution(Distribution.DistributionType.LPLPO)
		special_dist = self._create_distribution(Distribution.DistributionType.SPECIAL_REQUEST)

		response = self.client.get(reverse('reports:numbering_history'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, lplpo_dist.document_number)
		self.assertContains(response, special_dist.document_number)
		self.assertContains(response, "Riwayat Penomoran")
		self.assertContains(response, "Lihat Dokumen")

	def test_numbering_history_page_filters_by_document_type(self):
		lplpo_dist = self._create_distribution(Distribution.DistributionType.LPLPO)
		self._create_distribution(Distribution.DistributionType.SPECIAL_REQUEST)

		response = self.client.get(
			reverse('reports:numbering_history'),
			{'distribution_type': Distribution.DistributionType.LPLPO, 'year': 2026},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, lplpo_dist.document_number)
		self.assertNotContains(response, 'KD.F/2026')

	def test_numbering_history_page_shows_print_and_export_actions(self):
		self._create_distribution(Distribution.DistributionType.LPLPO)

		response = self.client.get(reverse('reports:numbering_history'))

		self.assertContains(response, 'Cetak Laporan')
		self.assertContains(response, 'Export Excel')

	def test_numbering_history_excel_export_returns_workbook(self):
		self._create_distribution(Distribution.DistributionType.LPLPO)

		response = self.client.get(
			reverse('reports:numbering_history'),
			{'year': 2026, 'format': 'excel'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response['Content-Type'],
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
		)
		self.assertIn('Riwayat_Penomoran_2026.xlsx', response['Content-Disposition'])
