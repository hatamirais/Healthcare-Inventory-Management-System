"""
Role-based access control decorators for Healthcare IMS.

Usage:
    @role_required('ADMIN', 'GUDANG', 'KEPALA')
    def my_view(request):
        ...
"""

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render


def role_required(*allowed_roles):
    """
    Decorator that restricts view access to users with specific roles.

    Must be used AFTER @login_required to ensure request.user is authenticated.
    Returns 403 Forbidden if the user's role is not in the allowed list.
    Superusers always pass the check.

    Args:
        *allowed_roles: One or more role strings (e.g., 'ADMIN', 'GUDANG', 'KEPALA').
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1>'
                '<p>Anda tidak memiliki izin untuk mengakses halaman ini.</p>'
            )
        return _wrapped_view
    return decorator
