from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='index'),
    path('riwayat-penomoran/', views.reports_numbering_history, name='numbering_history'),
    path('rekap/', views.reports_rekap, name='rekap'),
    path('penerimaan-hibah/', views.reports_penerimaan_hibah, name='penerimaan_hibah'),
    path('pengadaan/', views.reports_pengadaan, name='pengadaan'),
    path('kadaluarsa/', views.reports_kadaluarsa, name='kadaluarsa'),
    path('pengeluaran/', views.reports_pengeluaran, name='pengeluaran'),
]
