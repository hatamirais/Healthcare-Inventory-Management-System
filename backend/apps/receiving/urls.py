from django.urls import path
from . import views

app_name = 'receiving'

urlpatterns = [
    path('', views.receiving_list, name='receiving_list'),
    path('create/', views.receiving_create, name='receiving_create'),
    path('<int:pk>/', views.receiving_detail, name='receiving_detail'),
    path('api/quick-create-supplier/', views.quick_create_supplier, name='quick_create_supplier'),
    path('api/quick-create-funding-source/', views.quick_create_funding_source, name='quick_create_funding_source'),
]
