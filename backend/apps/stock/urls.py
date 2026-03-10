from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('stock-card/', views.stock_card_select, name='stock_card_select'),
    path('stock-card/<int:item_id>/', views.stock_card_detail, name='stock_card_detail'),
    path('api/item-search/', views.api_item_search, name='api_item_search'),
]
