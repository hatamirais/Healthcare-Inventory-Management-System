from django.db import transaction
from django.utils import timezone

from apps.stock.models import Stock, Transaction

from .models import Allocation


class AllocationWorkflowError(ValueError):
    pass


def _save_allocation(allocation, update_fields):
    allocation.save(update_fields=[*update_fields, "updated_at"])


def _get_allocation_items(allocation, action_label):
    allocation_items = list(
        allocation.items.select_related("facility", "item", "stock")
    )
    if not allocation_items:
        raise AllocationWorkflowError(
            f"Alokasi tidak memiliki item untuk {action_label}."
        )
    return allocation_items


def _validate_allocation_item_for_stock_workflow(allocation_item, action_label):
    if allocation_item.quantity is None or allocation_item.quantity <= 0:
        raise AllocationWorkflowError(
            f"Item {allocation_item.item.nama_barang}: jumlah harus diisi dan lebih dari 0."
        )

    if allocation_item.stock is None:
        raise AllocationWorkflowError(
            f"Item {allocation_item.item.nama_barang}: batch stok harus dipilih sebelum {action_label}."
        )

    if allocation_item.stock.item_id != allocation_item.item_id:
        raise AllocationWorkflowError(
            f"Item {allocation_item.item.nama_barang}: batch stok tidak sesuai dengan barang yang dipilih."
        )

    if allocation_item.quantity > allocation_item.stock.available_quantity:
        raise AllocationWorkflowError(
            f"Stok tidak cukup untuk {allocation_item.item.nama_barang}. "
            f"Tersedia {allocation_item.stock.available_quantity}, diminta {allocation_item.quantity}."
        )


def execute_allocation_submission(allocation, user):
    if not allocation.selected_facilities.exists():
        raise AllocationWorkflowError(
            "Pilih minimal 1 fasilitas tujuan sebelum mengajukan alokasi."
        )

    if not allocation.staff_assignments.exists():
        raise AllocationWorkflowError(
            "Pilih minimal 1 petugas sebelum mengajukan alokasi."
        )

    allocation_items = _get_allocation_items(allocation, "diajukan")

    for allocation_item in allocation_items:
        _validate_allocation_item_for_stock_workflow(allocation_item, "pengajuan")

    allocation.status = Allocation.Status.SUBMITTED
    allocation.submitted_by = user
    allocation.submitted_at = timezone.now()
    _save_allocation(allocation, ["status", "submitted_by", "submitted_at"])


def execute_allocation_approval(allocation, user):
    _get_allocation_items(allocation, "disetujui")

    allocation.status = Allocation.Status.APPROVED
    allocation.approved_by = user
    allocation.approved_at = timezone.now()
    _save_allocation(allocation, ["status", "approved_by", "approved_at"])


def execute_allocation_rejection(allocation):
    allocation.status = Allocation.Status.REJECTED
    _save_allocation(allocation, ["status"])


def execute_allocation_preparation(allocation, user):
    _get_allocation_items(allocation, "disiapkan")

    allocation.status = Allocation.Status.PREPARED
    allocation.prepared_by = user
    allocation.prepared_at = timezone.now()
    _save_allocation(allocation, ["status", "prepared_by", "prepared_at"])


def execute_allocation_distribution(allocation, user):
    allocation_items = _get_allocation_items(allocation, "didistribusikan")
    processed_at = timezone.now()

    with transaction.atomic():
        for allocation_item in allocation_items:
            _validate_allocation_item_for_stock_workflow(
                allocation_item,
                "distribusi",
            )

            stock = Stock.objects.select_for_update().get(pk=allocation_item.stock_id)

            if stock.item_id != allocation_item.item_id:
                raise AllocationWorkflowError(
                    f"Batch stok tidak sesuai untuk item {allocation_item.item.nama_barang}."
                )

            if allocation_item.quantity > stock.available_quantity:
                raise AllocationWorkflowError(
                    f"Stok tidak cukup untuk {allocation_item.item.nama_barang}. "
                    f"Tersedia {stock.available_quantity}, diminta {allocation_item.quantity}."
                )

            stock.quantity = stock.quantity - allocation_item.quantity
            stock.save(update_fields=["quantity", "updated_at"])

            allocation_item.issued_batch_lot = stock.batch_lot
            allocation_item.issued_expiry_date = stock.expiry_date
            allocation_item.issued_unit_price = stock.unit_price
            allocation_item.issued_sumber_dana = stock.sumber_dana
            allocation_item.save(
                update_fields=[
                    "issued_batch_lot",
                    "issued_expiry_date",
                    "issued_unit_price",
                    "issued_sumber_dana",
                ]
            )

            Transaction.objects.create(
                transaction_type=Transaction.TransactionType.OUT,
                item=allocation_item.item,
                location=stock.location,
                batch_lot=stock.batch_lot,
                quantity=allocation_item.quantity,
                unit_price=stock.unit_price,
                sumber_dana=stock.sumber_dana,
                reference_type=Transaction.ReferenceType.ALLOCATION,
                reference_id=allocation.id,
                user=user,
                notes=(
                    f"Alokasi {allocation.document_number} ke {allocation_item.facility.name}: "
                    f"{allocation_item.notes}"
                ).strip(),
            )

        allocation.status = Allocation.Status.DISTRIBUTED
        allocation.distributed_by = user
        allocation.distributed_at = processed_at
        allocation.distributed_date = processed_at.date()
        _save_allocation(
            allocation,
            ["status", "distributed_by", "distributed_at", "distributed_date"],
        )


def execute_allocation_reset_to_draft(allocation):
    allocation.status = Allocation.Status.DRAFT
    allocation.submitted_by = None
    allocation.submitted_at = None
    allocation.approved_by = None
    allocation.approved_at = None
    allocation.prepared_by = None
    allocation.prepared_at = None
    allocation.distributed_by = None
    allocation.distributed_at = None
    allocation.distributed_date = None
    _save_allocation(
        allocation,
        [
            "status",
            "submitted_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "prepared_by",
            "prepared_at",
            "distributed_by",
            "distributed_at",
            "distributed_date",
        ],
    )