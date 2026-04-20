from django import forms
from django.db.models import F
from django.forms import inlineformset_factory

from apps.items.models import Facility
from apps.stock.models import Stock
from apps.users.models import User

from .models import Allocation, AllocationItem


class StockByItemSelect(forms.Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is not None and getattr(instance, "item_id", None):
            option.setdefault("attrs", {})["data-item-id"] = str(instance.item_id)
        return option


class AllocationForm(forms.ModelForm):
    selected_facilities = forms.ModelMultipleChoiceField(
        queryset=Facility.objects.filter(is_active=True).order_by("code", "name"),
        required=False,
        label="Fasilitas",
        widget=forms.CheckboxSelectMultiple,
        help_text="Pilih fasilitas tujuan yang akan menerima alokasi.",
    )
    assigned_staff = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("full_name", "username"),
        required=False,
        label="Petugas",
        widget=forms.CheckboxSelectMultiple,
        help_text="Pilih satu atau lebih petugas yang menyiapkan alokasi.",
    )

    class Meta:
        model = Allocation
        fields = ["document_number", "allocation_date", "notes"]
        widgets = {
            "document_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Kosongkan untuk auto-generate",
                }
            ),
            "allocation_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["selected_facilities"].initial = self.instance.selected_facilities.values_list(
                "facility_id", flat=True
            )
            self.fields["assigned_staff"].initial = self.instance.staff_assignments.values_list(
                "user_id", flat=True
            )


class AllocationItemForm(forms.ModelForm):
    class Meta:
        model = AllocationItem
        fields = ["facility", "item", "quantity", "stock", "notes"]
        widgets = {
            "facility": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "item": forms.Select(
                attrs={
                    "class": "form-select form-select-sm js-typeahead-select js-item-select"
                }
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control form-control-sm", "min": "1"}
            ),
            "stock": StockByItemSelect(
                attrs={"class": "form-select form-select-sm js-stock-select"}
            ),
            "notes": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
        }

    def __init__(self, *args, **kwargs):
        selected_facility_ids = kwargs.pop("selected_facility_ids", None)
        super().__init__(*args, **kwargs)
        self.fields["notes"].required = False
        self.fields["stock"].required = False

        if selected_facility_ids is None:
            if self.instance.pk and self.instance.allocation_id:
                selected_facility_ids = list(
                    self.instance.allocation.selected_facilities.values_list(
                        "facility_id", flat=True
                    )
                )
            else:
                selected_facility_ids = []

        posted_facility_id = None
        if self.is_bound:
            posted_facility_id = self.data.get(self.add_prefix("facility"))

        facility_ids_for_queryset = list(selected_facility_ids)
        if posted_facility_id:
            try:
                posted_facility_id = int(posted_facility_id)
            except (TypeError, ValueError):
                posted_facility_id = None
            if posted_facility_id and posted_facility_id not in facility_ids_for_queryset:
                facility_ids_for_queryset.append(posted_facility_id)

        self.fields["facility"].queryset = Facility.objects.filter(
            pk__in=facility_ids_for_queryset,
            is_active=True,
        ).order_by("code", "name")
        self.instance._selected_facility_ids_for_validation = set(selected_facility_ids)

        self.fields["stock"].queryset = (
            Stock.objects.select_related("item")
            .filter(quantity__gt=F("reserved"))
            .order_by("item_id", "expiry_date", "batch_lot")
        )
        self.fields["stock"].label_from_instance = lambda obj: (
            f"{obj.batch_lot} | Tersedia: {obj.available_quantity} | Exp: {obj.expiry_date}"
        )

    def clean(self):
        cleaned_data = super().clean()
        facility = cleaned_data.get("facility")
        item = cleaned_data.get("item")
        stock = cleaned_data.get("stock")
        quantity = cleaned_data.get("quantity")

        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Jumlah harus lebih dari 0.")

        if stock and item and stock.item_id != item.id:
            self.add_error("stock", "Batch stok harus sesuai dengan barang yang dipilih.")

        if (
            stock is not None
            and quantity is not None
            and quantity > stock.available_quantity
        ):
            self.add_error("quantity", "Jumlah melebihi stok batch yang tersedia.")

        if facility is None and item is not None:
            self.add_error("facility", "Pilih fasilitas tujuan untuk baris item ini.")

        return cleaned_data


AllocationItemFormSet = inlineformset_factory(
    Allocation,
    AllocationItem,
    form=AllocationItemForm,
    extra=3,
    can_delete=True,
)
