document.addEventListener('DOMContentLoaded', function () {
    function getAllocationStockCatalog() {
        var stockCatalogNode = document.getElementById('allocation-stock-catalog');
        if (!stockCatalogNode) return [];

        try {
            return JSON.parse(stockCatalogNode.textContent || '[]');
        } catch (_error) {
            return [];
        }
    }

    function syncPickerItemState(item) {
        if (!item) return;
        var checkbox = item.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        item.classList.toggle('is-selected', checkbox.checked);
    }

    function getSelectedFacilityOptions() {
        var facilityPicker = document.getElementById('allocation-facility-list');
        if (!facilityPicker) return [];

        return Array.from(
            facilityPicker.querySelectorAll('.selection-picker-item input[type="checkbox"]:checked')
        ).map(function (checkbox) {
            var item = checkbox.closest('.selection-picker-item');
            var label = item ? item.querySelector('.form-check-label') : null;
            return {
                value: checkbox.value,
                text: label ? label.textContent.trim() : checkbox.value,
            };
        });
    }

    function syncAllocationFacilitySelect(select) {
        if (!select) return;

        var currentValue = select.value;
        var facilityOptions = getSelectedFacilityOptions();
        var placeholderText = facilityOptions.length > 0
            ? 'Pilih fasilitas'
            : 'Pilih fasilitas di header';

        select.innerHTML = '';
        select.appendChild(new Option(placeholderText, ''));

        facilityOptions.forEach(function (option) {
            select.appendChild(new Option(option.text, option.value, false, option.value === currentValue));
        });

        if (!facilityOptions.some(function (option) { return option.value === currentValue; })) {
            select.value = '';
        }

        select.disabled = facilityOptions.length === 0;
    }

    function syncAllAllocationFacilitySelects() {
        document.querySelectorAll('select.js-allocation-row-facility').forEach(function (select) {
            syncAllocationFacilitySelect(select);
        });
    }

    function syncAllocationRowStockSelect(row) {
        if (!row) return;

        var itemSelect = row.querySelector('select.js-item-select');
        var stockSelect = row.querySelector('select.js-stock-select');
        if (!itemSelect || !stockSelect) return;

        var catalog = getAllocationStockCatalog();
        var selectedItemId = itemSelect.value;
        var currentValue = stockSelect.value;

        stockSelect.innerHTML = '';

        if (!selectedItemId) {
            stockSelect.appendChild(new Option('Pilih barang terlebih dahulu', ''));
            stockSelect.disabled = true;
            return;
        }

        stockSelect.appendChild(new Option('Pilih batch stok', ''));

        catalog
            .filter(function (entry) {
                return String(entry.itemId) === String(selectedItemId);
            })
            .forEach(function (entry) {
                stockSelect.appendChild(
                    new Option(entry.label, String(entry.id), false, String(entry.id) === String(currentValue))
                );
            });

        if (!catalog.some(function (entry) { return String(entry.id) === String(currentValue) && String(entry.itemId) === String(selectedItemId); })) {
            stockSelect.value = '';
        }

        stockSelect.disabled = false;
    }

    function bindAllocationRow(row) {
        if (!row || row.dataset.allocationRowBound === 'true') return;
        row.dataset.allocationRowBound = 'true';

        var itemSelect = row.querySelector('select.js-item-select');
        if (itemSelect) {
            itemSelect.addEventListener('change', function () {
                syncAllocationRowStockSelect(row);
            });
        }

        syncAllocationRowStockSelect(row);
    }

    function bindAllAllocationRows() {
        document.querySelectorAll('tr.formset-row').forEach(function (row) {
            bindAllocationRow(row);
        });
    }

    function updateSummary(picker) {
        var summary = picker.querySelector('.js-selection-summary');
        if (!summary) return;

        var checked = Array.from(picker.querySelectorAll('input[type="checkbox"]:checked'));
        if (checked.length === 0) {
            summary.textContent = summary.getAttribute('data-empty-summary') || 'Belum ada dipilih';
            return;
        }

        summary.textContent = checked.length + ' dipilih';
    }

    document.querySelectorAll('.selection-picker').forEach(function (picker) {
        picker.querySelectorAll('.selection-picker-item').forEach(function (item) {
            var checkbox = item.querySelector('input[type="checkbox"]');
            if (!checkbox) return;

            var syncState = function () {
                syncPickerItemState(item);
                updateSummary(picker);
                if (picker.querySelector('#allocation-facility-list, input[data-selection-filter-target="allocation-facility-list"]')) {
                    syncAllAllocationFacilitySelects();
                }
            };

            syncState();
            checkbox.addEventListener('change', syncState);
        });

        updateSummary(picker);
    });

    document.querySelectorAll('.js-selection-bulk-action').forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();

            var targetId = button.getAttribute('data-selection-target');
            var action = button.getAttribute('data-selection-action');
            var container = targetId ? document.getElementById(targetId) : null;
            var picker = button.closest('.selection-picker');
            if (!container || !picker) return;

            Array.from(container.querySelectorAll('.selection-picker-item input[type="checkbox"]')).forEach(function (checkbox) {
                var shouldCheck = action === 'select-all';
                if (checkbox.checked === shouldCheck) {
                    syncPickerItemState(checkbox.closest('.selection-picker-item'));
                    return;
                }

                checkbox.checked = shouldCheck;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            });

            updateSummary(picker);
            if (targetId === 'allocation-facility-list') {
                syncAllAllocationFacilitySelects();
            }
        });
    });

    var allocationFormsetContainer = document.querySelector('[data-formset="allocation-items"]');
    if (allocationFormsetContainer) {
        var tableBody = allocationFormsetContainer.querySelector('tbody');
        if (tableBody && typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function () {
                syncAllAllocationFacilitySelects();
                bindAllAllocationRows();
            });
            observer.observe(tableBody, { childList: true, subtree: true });
        }
    }

    document.querySelectorAll('.formset-add[data-formset-target="allocation-items"]').forEach(function (button) {
        button.addEventListener('click', function () {
            window.setTimeout(function () {
                syncAllAllocationFacilitySelects();
                bindAllAllocationRows();
            }, 0);
        });
    });

    syncAllAllocationFacilitySelects();
    bindAllAllocationRows();

    document.querySelectorAll('.js-selection-filter').forEach(function (input) {
        var targetId = input.getAttribute('data-selection-filter-target');
        var container = targetId ? document.getElementById(targetId) : null;
        if (!container) return;

        var items = Array.from(container.querySelectorAll('.selection-picker-item'));
        var emptyState = container.querySelector('.selection-picker-empty');

        input.addEventListener('input', function () {
            var query = input.value.trim().toLowerCase();
            var visibleCount = 0;

            items.forEach(function (item) {
                var label = item.getAttribute('data-selection-label') || '';
                var match = !query || label.includes(query);
                item.classList.toggle('d-none', !match);
                if (match) visibleCount += 1;
            });

            if (emptyState) {
                emptyState.classList.toggle('d-none', visibleCount > 0);
            }
        });
    });
});