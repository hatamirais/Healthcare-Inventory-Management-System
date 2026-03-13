from decimal import Decimal, InvalidOperation

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
