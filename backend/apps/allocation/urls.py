from django.urls import path

from . import views

app_name = "allocation"

urlpatterns = [
    path("", views.allocation_list, name="allocation_list"),
    path("create/", views.allocation_create, name="allocation_create"),
    path("<int:pk>/", views.allocation_detail, name="allocation_detail"),
    path("<int:pk>/edit/", views.allocation_edit, name="allocation_edit"),
]
