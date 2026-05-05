"""
Permission-based access control decorators for Healthcare IMS.

perm_required: Checks Django permissions (managed via Groups in Admin panel)
               with fallback to module-scope access model.
module_scope_required: Checks minimum module scope level.

Usage:
    @perm_required('receiving.add_receiving')
    def my_view(request):
        ...

    # Multiple permissions (user needs ANY one of them):
    @perm_required('recall.change_recall', 'recall.delete_recall')
    def my_view(request):
        ...
"""

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.users.access import has_module_permission, has_module_scope


def perm_required(*perms):
    """
    Decorator that restricts view access to users with specific Django permissions.

    Uses Django's permission framework — permissions are assigned via Groups
    in the Admin panel. No code changes needed to adjust access.

    Must be used AFTER @login_required to ensure request.user is authenticated.
    Returns 403 Forbidden if the user lacks ALL of the listed permissions.
    Superusers always pass the check (Django's has_perm returns True for superusers).

    Args:
        *perms: One or more permission strings (e.g., 'receiving.add_receiving').
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Superusers bypass all permission checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # User needs ANY one of the listed permissions
            if any(request.user.has_perm(p) for p in perms):
                return view_func(request, *args, **kwargs)

            # Fallback to module-role access model
            if any(has_module_permission(request.user, p) for p in perms):
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>Anda tidak memiliki izin untuk mengakses halaman ini.</p>"
            )

        return _wrapped_view

    return decorator



def module_scope_required(module: str, min_scope: int):
    """Restrict access to users with minimum scope in a module."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if has_module_scope(request.user, module, min_scope):
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>Anda tidak memiliki level akses modul yang diperlukan.</p>"
            )

        return _wrapped_view

    return decorator
