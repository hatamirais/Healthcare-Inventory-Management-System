from django.urls import path

from . import views

app_name = "allocation"

urlpatterns = [
    path("", views.allocation_list, name="allocation_list"),
    path("create/", views.allocation_create, name="allocation_create"),
    path("<int:pk>/", views.allocation_detail, name="allocation_detail"),
    path("<int:pk>/edit/", views.allocation_edit, name="allocation_edit"),
    path("<int:pk>/delete/", views.allocation_delete, name="allocation_delete"),
    path(
        "<int:pk>/reset-to-draft/",
        views.allocation_reset_to_draft,
        name="allocation_reset_to_draft",
    ),
    path("<int:pk>/submit/", views.allocation_submit, name="allocation_submit"),
    path("<int:pk>/approve/", views.allocation_approve, name="allocation_approve"),
    path("<int:pk>/reject/", views.allocation_reject, name="allocation_reject"),
    path("<int:pk>/prepare/", views.allocation_prepare, name="allocation_prepare"),
    path(
        "<int:pk>/distribute/",
        views.allocation_distribute,
        name="allocation_distribute",
    ),
]
