from django.contrib import admin

from .models import (
    Allocation,
    AllocationFacility,
    AllocationItem,
    AllocationItemFacility,
    AllocationStaffAssignment,
)


class AllocationFacilityInline(admin.TabularInline):
    model = AllocationFacility
    extra = 1
    raw_id_fields = ("facility",)


class AllocationItemFacilityInline(admin.TabularInline):
    model = AllocationItemFacility
    extra = 1
    raw_id_fields = ("facility",)


class AllocationItemInline(admin.TabularInline):
    model = AllocationItem
    extra = 1
    raw_id_fields = ("item", "stock")


class AllocationStaffAssignmentInline(admin.TabularInline):
    model = AllocationStaffAssignment
    extra = 1
    raw_id_fields = ("user",)


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = (
        "document_number",
        "sumber_dana",
        "allocation_date",
        "status",
        "created_by",
    )
    list_filter = ("status", "allocation_date", "sumber_dana")
    search_fields = (
        "document_number",
        "referensi",
        "notes",
        "created_by__username",
        "created_by__full_name",
    )
    date_hierarchy = "allocation_date"
    raw_id_fields = (
        "sumber_dana",
        "created_by",
        "submitted_by",
        "approved_by",
    )
    readonly_fields = (
        "submitted_at",
        "approved_at",
    )
    inlines = [
        AllocationStaffAssignmentInline,
        AllocationFacilityInline,
        AllocationItemInline,
    ]


@admin.register(AllocationItem)
class AllocationItemAdmin(admin.ModelAdmin):
    list_display = ("allocation", "item", "total_qty_available")
    raw_id_fields = ("allocation", "item", "stock")
    inlines = [AllocationItemFacilityInline]
