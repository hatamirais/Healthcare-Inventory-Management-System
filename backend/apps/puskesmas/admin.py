from django.contrib import admin
from .models import PuskesmasRequest, PuskesmasRequestItem


class PuskesmasRequestItemInline(admin.TabularInline):
    model = PuskesmasRequestItem
    extra = 1
    readonly_fields = ["created_at"]


@admin.register(PuskesmasRequest)
class PuskesmasRequestAdmin(admin.ModelAdmin):
    list_display = [
        "document_number",
        "facility",
        "program",
        "status",
        "request_date",
        "created_by",
    ]
    list_filter = ["status", "facility", "program"]
    search_fields = ["document_number", "facility__name"]
    readonly_fields = ["document_number", "created_by", "approved_by", "approved_at", "distribution"]
    inlines = [PuskesmasRequestItemInline]
