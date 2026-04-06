from django.urls import path
from . import views

app_name = 'recall'

urlpatterns = [
    path('', views.recall_list, name='recall_list'),
    path('create/', views.recall_create, name='recall_create'),
    path('<int:pk>/', views.recall_detail, name='recall_detail'),
    path('<int:pk>/edit/', views.recall_edit, name='recall_edit'),
    path('<int:pk>/reset-to-draft/', views.recall_reset_to_draft, name='recall_reset_to_draft'),
    path('<int:pk>/step-back/', views.recall_step_back, name='recall_step_back'),
    path('<int:pk>/submit/', views.recall_submit, name='recall_submit'),
    path('<int:pk>/verify/', views.recall_verify, name='recall_verify'),
    path('<int:pk>/complete/', views.recall_complete, name='recall_complete'),
    path('<int:pk>/delete/', views.recall_delete, name='recall_delete'),
]
