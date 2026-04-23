from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from django import template


register = template.Library()


def _to_decimal(value):
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


@register.filter
def id_decimal(value, places=2):
    """Format number with Indonesian separators (1.234.567,89)."""
    number = _to_decimal(value)

    try:
        places_int = int(places)
    except (TypeError, ValueError):
        places_int = 2

    if places_int < 0:
        places_int = 0

    formatted = f"{number:,.{places_int}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter
def idr(value):
    """Format currency in Indonesian Rupiah style."""
    return f"Rp {id_decimal(value, 0)}"


@register.filter
def safe_media_url(value):
    """Allow only root-relative media URLs or explicit http(s) URLs."""
    if not value:
        return ""

    try:
        url = str(value).strip()
    except Exception:
        return ""

    if not url:
        return ""

    parsed = urlparse(url)
    if url.startswith("/") and not parsed.scheme and not parsed.netloc:
        return url

    if parsed.scheme in {"http", "https"}:
        return url

    return ""
