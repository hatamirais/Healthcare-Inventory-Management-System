from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Stock, Transaction
from apps.items.models import Category, Location, FundingSource, Item
from django.http import JsonResponse
from datetime import datetime


@login_required
def stock_list(request):
    queryset = (
        Stock.objects.select_related('item', 'location', 'sumber_dana')
        .filter(quantity__gt=0)
        .order_by('item__nama_barang', 'expiry_date')
    )

    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(item__kode_barang__icontains=search) |
            Q(item__nama_barang__icontains=search) |
            Q(batch_lot__icontains=search)
        )

    location = request.GET.get('location')
    if location:
        queryset = queryset.filter(location_id=location)

    sumber_dana = request.GET.get('sumber_dana')
    if sumber_dana:
        queryset = queryset.filter(sumber_dana_id=sumber_dana)

    paginator = Paginator(queryset, 25)
    stocks = paginator.get_page(request.GET.get('page'))

    # Build filter lists with selected state
    locations = []
    for loc in Location.objects.filter(is_active=True):
        locations.append({
            'id': loc.id,
            'name': loc.name,
            'selected': 'selected' if location == str(loc.id) else '',
        })

    funding_sources = []
    for sd in FundingSource.objects.filter(is_active=True):
        funding_sources.append({
            'id': sd.id,
            'name': sd.name,
            'selected': 'selected' if sumber_dana == str(sd.id) else '',
        })

    return render(request, 'stock/stock_list.html', {
        'stocks': stocks,
        'locations': locations,
        'funding_sources': funding_sources,
        'search': search,
        'selected_location': location or '',
        'selected_sumber_dana': sumber_dana or '',
    })


@login_required
def transaction_list(request):
    queryset = (
        Transaction.objects.select_related('item', 'user', 'location')
        .order_by('-created_at')
    )

    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(item__kode_barang__icontains=search) |
            Q(item__nama_barang__icontains=search) |
            Q(batch_lot__icontains=search) |
            Q(notes__icontains=search)
        )

    tx_type = request.GET.get('type')
    if tx_type:
        queryset = queryset.filter(transaction_type=tx_type)

    paginator = Paginator(queryset, 25)
    transactions = paginator.get_page(request.GET.get('page'))

    return render(request, 'stock/transaction_list.html', {
        'transactions': transactions,
        'search': search,
        'selected_type': tx_type or '',
        'type_in': 'selected' if tx_type == 'IN' else '',
        'type_out': 'selected' if tx_type == 'OUT' else '',
        'type_adjust': 'selected' if tx_type == 'ADJUST' else '',
        'type_return': 'selected' if tx_type == 'RETURN' else '',
    })


@login_required
def stock_card_select(request):
    """Landing page for selecting an item to view its stock card."""
    return render(request, 'stock/stock_card_select.html')


@login_required
def stock_card_detail(request, item_id):
    """View the stock card (running balance) for a specific item."""
    from django.shortcuts import get_object_or_404
    from decimal import Decimal
    
    item = get_object_or_404(Item, pk=item_id)
    
    # Query all transactions for this item, sorted chronologically
    queryset = Transaction.objects.filter(item=item).select_related('location', 'user').order_by('created_at', 'id')
    
    location_id = request.GET.get('location')
    if location_id:
        queryset = queryset.filter(location_id=location_id)
        
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Optional date filters
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
        
    # Before paginating or rendering, we need the opening balance
    # Opening balance is the sum of transactions before date_from (if date_from is provided)
    opening_balance = Decimal('0')
    if date_from:
        past_txs = Transaction.objects.filter(item=item, created_at__date__lt=date_from)
        if location_id:
            past_txs = past_txs.filter(location_id=location_id)
            
        for tx in past_txs:
            if tx.transaction_type in [Transaction.TransactionType.IN, Transaction.TransactionType.RETURN]:
                opening_balance += tx.quantity
            elif tx.transaction_type in [Transaction.TransactionType.OUT, Transaction.TransactionType.ADJUST]:
                # Assume ADJUST is negative or positive, but we'll subtract OUT.
                # Standard convention for this app seems to be OUT is positive quantity, deducted.
                opening_balance -= tx.quantity

    # Fetch all matching transactions to calculate running balances
    transactions = list(queryset)
    
    current_balance = opening_balance
    total_in = Decimal('0')
    total_out = Decimal('0')
    
    for tx in transactions:
        tx_in = Decimal('0')
        tx_out = Decimal('0')
        
        if tx.transaction_type in [Transaction.TransactionType.IN, Transaction.TransactionType.RETURN]:
            tx_in = tx.quantity
            current_balance += tx_in
            total_in += tx_in
        else:
            tx_out = tx.quantity
            current_balance -= tx_out
            total_out += tx_out
            
        # Attach dynamic attributes
        tx.tx_in = tx_in
        tx.tx_out = tx_out
        tx.running_balance = current_balance

    # Pagination
    paginator = Paginator(transactions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare locations for filter dropdown
    locations = []
    for loc in Location.objects.filter(is_active=True):
        locations.append({
            'id': loc.id,
            'name': loc.name,
            'selected': 'selected' if location_id == str(loc.id) else '',
        })

    context = {
        'item': item,
        'transactions': page_obj,
        'opening_balance': opening_balance,
        'closing_balance': current_balance,
        'total_in': total_in,
        'total_out': total_out,
        'date_from': date_from or '',
        'date_to': date_to or '',
        'locations': locations,
        'selected_location': location_id or '',
    }
    return render(request, 'stock/stock_card_detail.html', context)


@login_required
def api_item_search(request):
    """AJAX endpoint for item typeahead."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})
        
    items = Item.objects.filter(is_active=True).filter(
        Q(kode_barang__icontains=q) | 
        Q(nama_barang__icontains=q)
    ).select_related('satuan', 'kategori')[:20]
    
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'text': f"{item.kode_barang} - {item.nama_barang}",
            'satuan': item.satuan.name if item.satuan else '',
            'kategori': item.kategori.name if item.kategori else '',
            'stock': sum([s.quantity for s in item.stock_entries.all()]) # Quick stock sum
        })
        
    return JsonResponse({'results': results})
