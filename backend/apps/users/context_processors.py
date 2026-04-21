from .access import has_module_scope
from .models import ModuleAccess
from django.conf import settings


def access_flags(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "can_view_user_management": False,
            "can_open_admin_panel": False,
            "can_view_items": False,
            "can_view_stock": False,
            "can_view_receiving": False,
            "can_view_distribution": False,
            "can_view_allocation": False,
            "can_view_recall": False,
            "can_view_expired": False,
            "can_view_stock_opname": False,
            "can_view_reports": False,
            "can_view_puskesmas": False,
            "can_view_lplpo": False,
        }

    return {
        "can_view_user_management": has_module_scope(
            user, ModuleAccess.Module.USERS, ModuleAccess.Scope.VIEW
        ),
        "can_open_admin_panel": has_module_scope(
            user, ModuleAccess.Module.ADMIN_PANEL, ModuleAccess.Scope.MANAGE
        ),
        "can_view_items": has_module_scope(
            user, ModuleAccess.Module.ITEMS, ModuleAccess.Scope.VIEW
        ),
        "can_view_stock": has_module_scope(
            user, ModuleAccess.Module.STOCK, ModuleAccess.Scope.VIEW
        ),
        "can_view_receiving": has_module_scope(
            user, ModuleAccess.Module.RECEIVING, ModuleAccess.Scope.VIEW
        ),
        "can_view_distribution": has_module_scope(
            user, ModuleAccess.Module.DISTRIBUTION, ModuleAccess.Scope.VIEW
        ),
        "can_view_allocation": settings.FEATURE_ALLOCATION_UI_ENABLED
        and has_module_scope(user, ModuleAccess.Module.ALLOCATION, ModuleAccess.Scope.VIEW),
        "can_view_recall": has_module_scope(
            user, ModuleAccess.Module.RECALL, ModuleAccess.Scope.VIEW
        ),
        "can_view_expired": has_module_scope(
            user, ModuleAccess.Module.EXPIRED, ModuleAccess.Scope.VIEW
        ),
        "can_view_stock_opname": has_module_scope(
            user, ModuleAccess.Module.STOCK_OPNAME, ModuleAccess.Scope.VIEW
        ),
        "can_view_reports": has_module_scope(
            user, ModuleAccess.Module.REPORTS, ModuleAccess.Scope.VIEW
        ),
        "can_view_puskesmas": has_module_scope(
            user, ModuleAccess.Module.PUSKESMAS, ModuleAccess.Scope.VIEW
        ),
        "can_view_lplpo": has_module_scope(
            user, ModuleAccess.Module.LPLPO, ModuleAccess.Scope.VIEW
        ),
    }
