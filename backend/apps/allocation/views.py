from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.decorators import module_scope_required, perm_required
from apps.users.models import ModuleAccess

from .forms import AllocationForm, AllocationItemFormSet
from .models import Allocation
from .services import (
    AllocationWorkflowError,
    execute_allocation_approval,
    execute_allocation_distribution,
    execute_allocation_preparation,
    execute_allocation_rejection,
    execute_allocation_reset_to_draft,
    execute_allocation_submission,
)


def _redirect_allocation_detail(pk):
    return redirect("allocation:allocation_detail", pk=pk)


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
            "item_error_colspan": 5,
        },
    )


@login_required
@perm_required("allocation.change_allocation")
def allocation_edit(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if allocation.status != Allocation.Status.DRAFT:
        messages.error(request, "Hanya alokasi Draft yang dapat diubah.")
        return redirect("allocation:allocation_detail", pk=allocation.pk)

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
            "item_error_colspan": 5,
        },
    )


@login_required
@perm_required("allocation.change_allocation")
def allocation_submit(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status != Allocation.Status.DRAFT:
        messages.error(request, "Hanya alokasi Draft yang dapat diajukan.")
        return _redirect_allocation_detail(pk)

    try:
        execute_allocation_submission(allocation, request.user)
    except AllocationWorkflowError as exc:
        messages.error(request, str(exc))
        return _redirect_allocation_detail(pk)

    messages.success(request, f"Alokasi {allocation.document_number} berhasil diajukan.")
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.change_allocation")
@module_scope_required(ModuleAccess.Module.ALLOCATION, ModuleAccess.Scope.APPROVE)
def allocation_approve(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status != Allocation.Status.SUBMITTED:
        messages.error(request, "Hanya alokasi berstatus Diajukan yang dapat disetujui.")
        return _redirect_allocation_detail(pk)

    try:
        execute_allocation_approval(allocation, request.user)
    except AllocationWorkflowError as exc:
        messages.error(request, str(exc))
        return _redirect_allocation_detail(pk)

    messages.success(request, f"Alokasi {allocation.document_number} berhasil disetujui.")
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.change_allocation")
@module_scope_required(ModuleAccess.Module.ALLOCATION, ModuleAccess.Scope.APPROVE)
def allocation_reject(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status != Allocation.Status.SUBMITTED:
        messages.error(request, "Hanya alokasi berstatus Diajukan yang dapat ditolak.")
        return _redirect_allocation_detail(pk)

    execute_allocation_rejection(allocation)
    messages.success(request, f"Alokasi {allocation.document_number} ditolak.")
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.change_allocation")
def allocation_prepare(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status != Allocation.Status.APPROVED:
        messages.error(request, "Hanya alokasi disetujui yang dapat disiapkan.")
        return _redirect_allocation_detail(pk)

    try:
        execute_allocation_preparation(allocation, request.user)
    except AllocationWorkflowError as exc:
        messages.error(request, str(exc))
        return _redirect_allocation_detail(pk)

    messages.success(request, f"Alokasi {allocation.document_number} ditandai disiapkan.")
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.change_allocation")
def allocation_distribute(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status != Allocation.Status.PREPARED:
        messages.error(
            request,
            "Hanya alokasi berstatus Disiapkan yang dapat didistribusikan.",
        )
        return _redirect_allocation_detail(pk)

    try:
        execute_allocation_distribution(allocation, request.user)
    except AllocationWorkflowError as exc:
        messages.error(request, str(exc))
        return _redirect_allocation_detail(pk)

    messages.success(
        request,
        f"Alokasi {allocation.document_number} berhasil didistribusikan dan stok diperbarui.",
    )
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.change_allocation")
def allocation_reset_to_draft(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    resettable_statuses = {
        Allocation.Status.SUBMITTED,
        Allocation.Status.APPROVED,
        Allocation.Status.PREPARED,
        Allocation.Status.REJECTED,
    }

    if allocation.status not in resettable_statuses:
        if allocation.status == Allocation.Status.DISTRIBUTED:
            messages.error(
                request,
                "Alokasi yang sudah didistribusikan tidak dapat dikembalikan ke Draft.",
            )
        else:
            messages.error(
                request,
                "Status alokasi saat ini tidak dapat dikembalikan ke Draft.",
            )
        return _redirect_allocation_detail(pk)

    execute_allocation_reset_to_draft(allocation)
    messages.success(request, f"Alokasi {allocation.document_number} dikembalikan ke Draft.")
    return _redirect_allocation_detail(pk)


@login_required
@perm_required("allocation.delete_allocation")
def allocation_delete(request, pk):
    allocation = get_object_or_404(Allocation, pk=pk)
    if request.method != "POST":
        return _redirect_allocation_detail(pk)

    if allocation.status not in {Allocation.Status.DRAFT, Allocation.Status.REJECTED}:
        messages.error(
            request,
            "Hanya alokasi berstatus Draft atau Ditolak yang dapat dihapus.",
        )
        return _redirect_allocation_detail(pk)

    document_number = allocation.document_number
    allocation.delete()
    messages.success(request, f"Alokasi {document_number} berhasil dihapus.")
    return redirect("allocation:allocation_list")
