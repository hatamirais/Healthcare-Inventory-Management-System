from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Allocation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Diajukan"
        APPROVED = "APPROVED", "Disetujui"
        PREPARED = "PREPARED", "Disiapkan"
        DISTRIBUTED = "DISTRIBUTED", "Terdistribusi"
        REJECTED = "REJECTED", "Ditolak"

    document_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Leave blank to auto-generate (e.g., ALC-YYYYMM-XXXXX)",
    )
    allocation_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_allocations",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_allocations",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_allocations",
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="prepared_allocations",
    )
    distributed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="distributed_allocations",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    prepared_at = models.DateTimeField(null=True, blank=True)
    distributed_at = models.DateTimeField(null=True, blank=True)
    distributed_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "allocations"
        ordering = ["-allocation_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "allocation_date"], name="idx_alloc_status_date"),
        ]

    def __str__(self):
        return self.document_number or "Alokasi baru"

    def save(self, *args, **kwargs):
        if not self.document_number:
            prefix = f"ALC-{timezone.now().strftime('%Y%m')}-"
            last = (
                Allocation.objects.filter(document_number__startswith=prefix)
                .order_by("-document_number")
                .first()
            )
            if last:
                last_number = int(last.document_number.split("-")[-1])
                next_number = last_number + 1
            else:
                next_number = 1
            self.document_number = f"{prefix}{str(next_number).zfill(5)}"
        super().save(*args, **kwargs)


class AllocationStaffAssignment(TimeStampedModel):
    allocation = models.ForeignKey(
        Allocation,
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="allocation_staff_assignments",
    )

    class Meta:
        db_table = "allocation_staff_assignments"
        unique_together = ("allocation", "user")
        ordering = ["user__full_name", "user__username"]

    def __str__(self):
        return f"{self.allocation} - {self.user}"


class AllocationFacility(models.Model):
    allocation = models.ForeignKey(
        Allocation,
        on_delete=models.CASCADE,
        related_name="selected_facilities",
    )
    facility = models.ForeignKey(
        "items.Facility",
        on_delete=models.PROTECT,
        related_name="allocation_selections",
    )

    class Meta:
        db_table = "allocation_facilities"
        unique_together = ("allocation", "facility")
        ordering = ["facility__name"]

    def __str__(self):
        return f"{self.allocation} - {self.facility}"


class AllocationItem(models.Model):
    allocation = models.ForeignKey(
        Allocation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    facility = models.ForeignKey(
        "items.Facility",
        on_delete=models.PROTECT,
        related_name="allocation_items",
    )
    item = models.ForeignKey(
        "items.Item",
        on_delete=models.PROTECT,
        related_name="allocation_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.ForeignKey(
        "stock.Stock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="allocation_items",
    )
    issued_batch_lot = models.CharField(max_length=100, blank=True)
    issued_expiry_date = models.DateField(null=True, blank=True)
    issued_unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    issued_sumber_dana = models.ForeignKey(
        "items.FundingSource",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="issued_allocation_items",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "allocation_items"
        ordering = ["facility__name", "item__nama_barang"]

    def __str__(self):
        return f"{self.facility} - {self.item} x {self.quantity}"

    def clean(self):
        errors = {}

        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Jumlah harus lebih dari 0."

        if self.stock_id and self.item_id and self.stock.item_id != self.item_id:
            errors["stock"] = "Batch stok harus sesuai dengan barang yang dipilih."

        if (
            self.stock_id
            and self.quantity is not None
            and self.stock.available_quantity < self.quantity
        ):
            errors["quantity"] = "Jumlah melebihi stok batch yang tersedia."

        if self.facility_id:
            selected_facility_ids = getattr(
                self,
                "_selected_facility_ids_for_validation",
                None,
            )
            if selected_facility_ids is None and self.allocation_id:
                selected_facility_ids = set(
                    self.allocation.selected_facilities.values_list(
                        "facility_id", flat=True
                    )
                )

            selected = (
                self.facility_id in selected_facility_ids
                if selected_facility_ids is not None
                else True
            )
            if not selected:
                errors["facility"] = "Fasilitas item harus dipilih pada header alokasi."

        if errors:
            raise ValidationError(errors)
