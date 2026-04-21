document.addEventListener('DOMContentLoaded', function () {
    function syncPickerItemState(item) {
        if (!item) return;
        var checkbox = item.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        item.classList.toggle('is-selected', checkbox.checked);
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
        });
    });

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