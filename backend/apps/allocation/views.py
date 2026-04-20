from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.decorators import perm_required

from .forms import AllocationForm, AllocationItemFormSet
from .models import Allocation


def sync_allocation_staff_assignments(allocation, staff_users):
    selected_users = list(staff_users)
    selected_ids = {user.id for user in selected_users}

    allocation.staff_assignments.exclude(user_id__in=selected_ids).delete()

    existing_ids = set(
        allocation.staff_assignments.filter(user_id__in=selected_ids).values_list(
            "user_id", flat=True
        )
    )

    allocation.staff_assignments.model.objects.bulk_create(
        [
            allocation.staff_assignments.model(allocation=allocation, user=user)
            for user in selected_users
            if user.id not in existing_ids
        ]
    )


def sync_allocation_selected_facilities(allocation, facilities):
    selected_facilities = list(facilities)
    selected_ids = {facility.id for facility in selected_facilities}

    allocation.selected_facilities.exclude(facility_id__in=selected_ids).delete()

    existing_ids = set(
        allocation.selected_facilities.filter(facility_id__in=selected_ids).values_list(
            "facility_id", flat=True
        )
    )

    allocation.selected_facilities.model.objects.bulk_create(
        [
            allocation.selected_facilities.model(allocation=allocation, facility=facility)
            for facility in selected_facilities
            if facility.id not in existing_ids
        ]
    )


def _selected_facility_ids_from_request(request, instance=None):
    selected_ids = request.POST.getlist("selected_facilities") if request.method == "POST" else []
    if selected_ids:
        return [int(facility_id) for facility_id in selected_ids if facility_id]
    if instance and instance.pk:
        return list(instance.selected_facilities.values_list("facility_id", flat=True))
    return []


@login_required
@perm_required("allocation.view_allocation")
def allocation_list(request):
    queryset = (
        Allocation.objects.select_related("created_by")
        .annotate(
            facility_count=Count("selected_facilities", distinct=True),
            staff_count=Count("staff_assignments", distinct=True),
            item_count=Count("items", distinct=True),
        )
        .order_by("-allocation_date", "-created_at")
    )

    search = request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(document_number__icontains=search)
            | Q(notes__icontains=search)
            | Q(created_by__username__icontains=search)
            | Q(created_by__full_name__icontains=search)
            | Q(selected_facilities__facility__name__icontains=search)
            | Q(items__item__nama_barang__icontains=search)
            | Q(staff_assignments__user__full_name__icontains=search)
            | Q(staff_assignments__user__username__icontains=search)
        ).distinct()

    status = request.GET.get("status", "").strip()
    if status:
        queryset = queryset.filter(status=status)

    allocations = Paginator(queryset, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "allocation/allocation_list.html",
        {
            "allocations": allocations,
            "search": search,
            "selected_status": status,
            "status_choices": Allocation.Status.choices,
            "page_title": "Alokasi Barang",
        },
    )


@login_required
@perm_required("allocation.view_allocation")
def allocation_detail(request, pk):
    allocation = get_object_or_404(
        Allocation.objects.select_related(
            "created_by",
            "submitted_by",
            "approved_by",
            "prepared_by",
            "distributed_by",
        ).prefetch_related(
            "selected_facilities__facility",
            "staff_assignments__user",
            "items__facility",
            "items__item",
            "items__item__satuan",
            "items__stock",
        ),
        pk=pk,
    )

    return render(
        request,
        "allocation/allocation_detail.html",
        {
            "allocation": allocation,
            "selected_facilities": [entry.facility for entry in allocation.selected_facilities.all()],
            "assigned_staff": [entry.user for entry in allocation.staff_assignments.all()],
            "items": allocation.items.all(),
            "page_title": "Detail Alokasi",
        },
    )


@login_required
@perm_required("allocation.add_allocation")
def allocation_create(request):
    selected_facility_ids = _selected_facility_ids_from_request(request)

    if request.method == "POST":
        form = AllocationForm(request.POST)
        formset = AllocationItemFormSet(
            request.POST,
            prefix="items",
            form_kwargs={"selected_facility_ids": selected_facility_ids},
        )

        if form.is_valid() and formset.is_valid():
            allocation = form.save(commit=False)
            allocation.created_by = request.user
            allocation.status = Allocation.Status.DRAFT
            allocation.save()

            sync_allocation_selected_facilities(
                allocation, form.cleaned_data.get("selected_facilities", [])
            )
            sync_allocation_staff_assignments(
                allocation, form.cleaned_data.get("assigned_staff", [])
            )

            formset.instance = allocation
            formset.save()

            messages.success(
                request, f"Alokasi {allocation.document_number} berhasil dibuat."
            )
            return redirect("allocation:allocation_detail", pk=allocation.pk)
    else:
        form = AllocationForm(initial={"allocation_date": timezone.now().date()})
        formset = AllocationItemFormSet(
            prefix="items",
            form_kwargs={"selected_facility_ids": selected_facility_ids},
        )

    return render(
        request,
        "allocation/allocation_form.html",
        {
            "title": "Buat Alokasi Baru",
            "page_title": "Buat Alokasi Baru",
            "form": form,
            "formset": formset,
            "is_edit": False,
            "item_error_colspan": 6,
        },
    )


@login_required
@perm_required("allocation.change_allocation")
def allocation_edit(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    selected_facility_ids = _selected_facility_ids_from_request(request, allocation)

    if request.method == "POST":
        form = AllocationForm(request.POST, instance=allocation)
        formset = AllocationItemFormSet(
            request.POST,
            instance=allocation,
            prefix="items",
            form_kwargs={"selected_facility_ids": selected_facility_ids},
        )

        if form.is_valid() and formset.is_valid():
            form.save()
            sync_allocation_selected_facilities(
                allocation, form.cleaned_data.get("selected_facilities", [])
            )
            sync_allocation_staff_assignments(
                allocation, form.cleaned_data.get("assigned_staff", [])
            )
            formset.save()

            messages.success(
                request, f"Alokasi {allocation.document_number} berhasil diperbarui."
            )
            return redirect("allocation:allocation_detail", pk=allocation.pk)
    else:
        form = AllocationForm(instance=allocation)
        formset = AllocationItemFormSet(
            instance=allocation,
            prefix="items",
            form_kwargs={"selected_facility_ids": selected_facility_ids},
        )

    return render(
        request,
        "allocation/allocation_form.html",
        {
            "title": f"Edit Alokasi {allocation.document_number}",
            "page_title": "Edit Alokasi",
            "allocation": allocation,
            "form": form,
            "formset": formset,
            "is_edit": True,
            "item_error_colspan": 6,
        },
    )
