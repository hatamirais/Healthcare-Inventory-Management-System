from django.contrib import admin

from .models import Allocation, AllocationFacility, AllocationItem, AllocationStaffAssignment


class AllocationFacilityInline(admin.TabularInline):
    model = AllocationFacility
    extra = 1
    raw_id_fields = ("facility",)


class AllocationItemInline(admin.TabularInline):
    model = AllocationItem
    extra = 1
    raw_id_fields = ("facility", "item", "stock", "issued_sumber_dana")


class AllocationStaffAssignmentInline(admin.TabularInline):
    model = AllocationStaffAssignment
    extra = 1
    raw_id_fields = ("user",)


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = (
        "document_number",
        "allocation_date",
        "status",
        "created_by",
    )
    list_filter = ("status", "allocation_date")
    search_fields = ("document_number", "notes", "created_by__username", "created_by__full_name")
    date_hierarchy = "allocation_date"
    raw_id_fields = (
        "created_by",
        "submitted_by",
        "approved_by",
        "prepared_by",
        "distributed_by",
    )
    readonly_fields = (
        "submitted_at",
        "approved_at",
        "prepared_at",
        "distributed_at",
        "distributed_date",
    )
    inlines = [
        AllocationStaffAssignmentInline,
        AllocationFacilityInline,
        AllocationItemInline,
    ]
