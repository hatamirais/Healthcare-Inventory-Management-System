from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper

from apps.items.models import Item
from apps.stock.models import Stock, Transaction


@login_required
def dashboard(request):
    today = timezone.now().date()
    three_months_later = today + timedelta(days=90)
    thirty_days_ago = today - timedelta(days=29)

    # Stats
    total_items = Item.objects.filter(is_active=True).count()
    total_stock_entries = Stock.objects.filter(quantity__gt=0).count()
    total_stock_quantity = Stock.objects.filter(quantity__gt=0).aggregate(
        total=Sum("quantity")
    )["total"] or Decimal("0")
    total_stock_value = Stock.objects.filter(quantity__gt=0).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity") * F("unit_price"),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
    ).get("total") or Decimal("0")

    # Low stock: items where total stock quantity is below minimum_stock
    low_stock_items = (
        Item.objects.filter(is_active=True)
        .annotate(total_qty=Sum("stock_entries__quantity"))
        .filter(
            Q(total_qty__lt=F("minimum_stock")) | Q(total_qty__isnull=True),
            minimum_stock__gt=0,
        )
    )
    low_stock_count = low_stock_items.count()

    # Expiring soon: stock entries expiring within 3 months
    expiring_soon = (
        Stock.objects.filter(
            quantity__gt=0,
            expiry_date__lte=three_months_later,
        )
        .select_related("item")
        .order_by("expiry_date")[:10]
    )
    expiring_soon_count = Stock.objects.filter(
        quantity__gt=0,
        expiry_date__lte=three_months_later,
    ).count()

    today_transaction_count = Transaction.objects.filter(created_at__date=today).count()
    tx_last_30_days = Transaction.objects.filter(created_at__date__gte=thirty_days_ago)
    inbound_30_days = tx_last_30_days.filter(
        transaction_type=Transaction.TransactionType.IN
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    outbound_30_days = tx_last_30_days.filter(
        transaction_type=Transaction.TransactionType.OUT
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    movement_total_30_days = inbound_30_days + outbound_30_days
    if movement_total_30_days > 0:
        inbound_percent_30_days = int((inbound_30_days / movement_total_30_days) * 100)
        outbound_percent_30_days = 100 - inbound_percent_30_days
    else:
        inbound_percent_30_days = 0
        outbound_percent_30_days = 0

    # Recent transactions
    recent_transactions = Transaction.objects.select_related("item", "user").order_by(
        "-created_at"
    )[:10]

    return render(
        request,
        "dashboard.html",
        {
            "total_items": total_items,
            "total_stock_entries": total_stock_entries,
            "total_stock_quantity": total_stock_quantity,
            "total_stock_value": total_stock_value,
            "low_stock_count": low_stock_count,
            "expiring_soon_count": expiring_soon_count,
            "expiring_soon": expiring_soon,
            "today_transaction_count": today_transaction_count,
            "inbound_30_days": inbound_30_days,
            "outbound_30_days": outbound_30_days,
            "inbound_percent_30_days": inbound_percent_30_days,
            "outbound_percent_30_days": outbound_percent_30_days,
            "thirty_days_ago": thirty_days_ago,
            "today": today,
            "recent_transactions": recent_transactions,
        },
    )
