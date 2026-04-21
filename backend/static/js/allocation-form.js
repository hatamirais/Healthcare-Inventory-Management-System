/**
 * Allocation Form — 4-step wizard with dynamic allocation matrix.
 *
 * Step 1: Info Umum (sumber_dana, referensi, facilities, staff)
 * Step 2: Item selection (formset with stock/batch selector)
 * Step 3: Facility allocation matrix (dynamic columns, real-time validation)
 * Step 4: Read-only review generated from form data
 */

document.addEventListener('DOMContentLoaded', () => {
    const stockCatalog = JSON.parse(
        document.getElementById('allocation-stock-catalog')?.textContent || '[]'
    );
    const facilityPickerMeta = JSON.parse(
        document.getElementById('allocation-facility-picker-meta')?.textContent || '{}'
    );
    const staffPickerMeta = JSON.parse(
        document.getElementById('allocation-staff-picker-meta')?.textContent || '{}'
    );

    let existingAllocations = {};
    const existingEl = document.getElementById('existing-allocations');
    if (existingEl) {
        try { existingAllocations = JSON.parse(existingEl.textContent || '{}'); }
        catch { existingAllocations = {}; }
    }

    // ────────────────────────────────────
    // Wizard navigation
    // ────────────────────────────────────

    const stepBtns = document.querySelectorAll('.wizard-step-btn');
    const panels = document.querySelectorAll('.wizard-panel');

    function goToStep(n) {
        stepBtns.forEach(btn => btn.classList.toggle('active', parseInt(btn.dataset.step) === n));
        panels.forEach(panel => panel.classList.toggle('active', panel.id === `step-${n}`));

        if (n === 3) buildMatrix();
        if (n === 4) buildReview();
    }

    stepBtns.forEach(btn => {
        btn.addEventListener('click', () => goToStep(parseInt(btn.dataset.step)));
    });

    document.querySelectorAll('.js-wizard-next').forEach(btn => {
        btn.addEventListener('click', () => goToStep(parseInt(btn.dataset.nextStep)));
    });

    document.querySelectorAll('.js-wizard-prev').forEach(btn => {
        btn.addEventListener('click', () => goToStep(parseInt(btn.dataset.prevStep)));
    });

    // ────────────────────────────────────
    // Stock catalog cascading (Step 2)
    // ────────────────────────────────────

    function handleItemChange(itemSelect) {
        const row = itemSelect.closest('tr');
        if (!row) return;
        const stockSelect = row.querySelector('.js-stock-select');
        if (!stockSelect) return;

        const selectedItemId = itemSelect.value;
        stockSelect.innerHTML = '<option value="">---------</option>';

        if (!selectedItemId) return;

        const matchingStocks = stockCatalog.filter(s => String(s.itemId) === String(selectedItemId));
        matchingStocks.forEach(stock => {
            const opt = document.createElement('option');
            opt.value = stock.id;
            opt.textContent = stock.label;
            opt.dataset.availableQty = stock.availableQty;
            stockSelect.appendChild(opt);
        });
    }

    function handleStockChange(stockSelect) {
        const row = stockSelect.closest('tr');
        if (!row) return;
        const qtyCell = row.querySelector('.js-available-qty');
        const hiddenQtyInput = row.querySelector('[name$="-total_qty_available"]');
        const selectedOption = stockSelect.options[stockSelect.selectedIndex];

        if (selectedOption && selectedOption.dataset.availableQty) {
            const qty = selectedOption.dataset.availableQty;
            if (qtyCell) qtyCell.textContent = qty;
            if (hiddenQtyInput) hiddenQtyInput.value = qty;
        } else {
            if (qtyCell) qtyCell.textContent = '—';
            if (hiddenQtyInput) hiddenQtyInput.value = '0';
        }
    }

    document.addEventListener('change', (e) => {
        if (e.target.matches('.js-item-select')) handleItemChange(e.target);
        if (e.target.matches('.js-stock-select')) handleStockChange(e.target);
    });

    function refreshDerivedViews() {
        if (document.getElementById('step-3')?.classList.contains('active')) buildMatrix();
        if (document.getElementById('step-4')?.classList.contains('active')) buildReview();
    }

    function getSelectionTitle(item, fallback = '') {
        return item?.querySelector('.selection-item-title')?.textContent?.trim()
            || item?.querySelector('.form-check-label')?.textContent?.trim()
            || fallback;
    }

    function enhancePickerList(listId, metadata) {
        const listEl = document.getElementById(listId);
        if (!listEl) return;

        getPickerItems(listEl).forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const label = item.querySelector('.form-check-label');
            if (!checkbox || !label) return;

            const meta = metadata[String(checkbox.value)];
            if (!meta) return;

            label.innerHTML = `
                <span class="selection-item-text">
                    <span class="selection-item-title">${escapeHtml(meta.title)}</span>
                    <span class="selection-item-description">${escapeHtml(meta.description)}</span>
                </span>
            `;
            item.dataset.selectionLabel = `${meta.title} ${meta.description}`.toLowerCase();
        });
    }

    function getPickerItems(listEl) {
        return Array.from(listEl.querySelectorAll('.selection-picker-item'));
    }

    function getVisiblePickerItems(listEl) {
        return getPickerItems(listEl).filter(item => !item.classList.contains('d-none'));
    }

    function updatePickerSummary(listEl) {
        const picker = listEl.closest('.selection-picker');
        const summaryEl = picker?.querySelector('.js-selection-summary');
        if (!summaryEl) return;

        const checkedItems = getPickerItems(listEl).filter(item => item.querySelector('input[type="checkbox"]:checked'));
        const emptySummary = summaryEl.dataset.emptySummary || 'Belum ada pilihan';

        if (checkedItems.length === 0) {
            summaryEl.textContent = emptySummary;
            return;
        }

        summaryEl.textContent = `${checkedItems.length} dipilih`;
    }

    function updatePickerItemState(checkbox) {
        const item = checkbox.closest('.selection-picker-item');
        if (!item) return;
        item.classList.toggle('is-selected', checkbox.checked);
    }

    function updatePickerEmptyState(listEl) {
        const emptyEl = listEl.querySelector('.selection-picker-empty');
        if (!emptyEl) return;
        emptyEl.classList.toggle('d-none', getVisiblePickerItems(listEl).length > 0);
    }

    function handlePickerFilter(input) {
        const listEl = document.getElementById(input.dataset.selectionFilterTarget || '');
        if (!listEl) return;

        const term = input.value.trim().toLowerCase();
        getPickerItems(listEl).forEach(item => {
            const label = item.dataset.selectionLabel || '';
            item.classList.toggle('d-none', Boolean(term) && !label.includes(term));
        });

        updatePickerEmptyState(listEl);
    }

    function applyBulkSelection(button) {
        const listEl = document.getElementById(button.dataset.selectionTarget || '');
        if (!listEl) return;

        const shouldSelect = button.dataset.selectionAction === 'select-all';
        getVisiblePickerItems(listEl).forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            if (!checkbox || checkbox.disabled) return;
            checkbox.checked = shouldSelect;
            updatePickerItemState(checkbox);
        });

        updatePickerSummary(listEl);
        refreshDerivedViews();
    }

    function initializeSelectionPickers() {
        enhancePickerList('allocation-facility-list', facilityPickerMeta);
        enhancePickerList('allocation-staff-list', staffPickerMeta);

        document.querySelectorAll('.selection-picker-list').forEach(listEl => {
            getPickerItems(listEl).forEach(item => {
                const checkbox = item.querySelector('input[type="checkbox"]');
                if (checkbox) updatePickerItemState(checkbox);
            });
            updatePickerSummary(listEl);
            updatePickerEmptyState(listEl);
        });

        document.querySelectorAll('.js-selection-filter').forEach(input => {
            input.addEventListener('input', () => handlePickerFilter(input));
        });

        document.querySelectorAll('.js-selection-bulk-action').forEach(button => {
            button.addEventListener('click', () => applyBulkSelection(button));
        });

        document.addEventListener('change', (e) => {
            if (!e.target.matches('.selection-picker input[type="checkbox"]')) return;
            const listEl = e.target.closest('.selection-picker-list');
            if (!listEl) return;

            updatePickerItemState(e.target);
            updatePickerSummary(listEl);
            refreshDerivedViews();
        });
    }

    initializeSelectionPickers();

    // ────────────────────────────────────
    // Matrix building (Step 3)
    // ────────────────────────────────────

    function getSelectedFacilities() {
        const facilities = [];
        document.querySelectorAll('#allocation-facility-list input[type="checkbox"]:checked')
            .forEach(cb => {
                const label = cb.closest('.selection-picker-item');
                const name = getSelectionTitle(label, cb.value);
                facilities.push({ id: cb.value, name: name });
            });
        return facilities;
    }

    function getFormsetItems() {
        const items = [];
        const formsetContainer = document.querySelector('[data-formset="allocation-items"]');
        if (!formsetContainer) return items;

        const rows = formsetContainer.querySelectorAll('.formset-row');
        rows.forEach((row) => {
            const deleteCheckbox = row.querySelector('[name$="-DELETE"]');
            if (deleteCheckbox && deleteCheckbox.checked) return;
            if (row.style.display === 'none') return;

            const itemSelect = row.querySelector('.js-item-select');
            const stockSelect = row.querySelector('.js-stock-select');
            const qtyCell = row.querySelector('.js-available-qty');
            const idField = row.querySelector('[name$="-id"]');

            if (!itemSelect || !itemSelect.value) return;

            const itemText = itemSelect.options[itemSelect.selectedIndex]?.text || '';
            const stockText = stockSelect?.options[stockSelect.selectedIndex]?.text || '';
            const available = parseFloat(qtyCell?.textContent) || 0;

            // Try to determine a stable ID for the matrix row
            const formIndex = idField?.value || itemSelect.name?.match(/items-(\d+)-/)?.[1] || '';

            items.push({
                formIndex: formIndex,
                itemId: itemSelect.value,
                itemName: itemText,
                stockId: stockSelect?.value || '',
                stockLabel: stockText,
                available: available,
            });
        });
        return items;
    }

    function buildMatrix() {
        const facilities = getSelectedFacilities();
        const items = getFormsetItems();
        const headerRow = document.getElementById('matrix-header-row');
        const matrixBody = document.getElementById('matrix-body');
        const emptyMsg = document.getElementById('matrix-empty-msg');

        if (!headerRow || !matrixBody) return;

        // Clear dynamic columns
        headerRow.querySelectorAll('.js-facility-col').forEach(el => el.remove());

        // Insert facility columns before "Total"
        const totalTh = headerRow.lastElementChild;
        facilities.forEach(f => {
            const th = document.createElement('th');
            th.textContent = f.name;
            th.classList.add('js-facility-col');
            headerRow.insertBefore(th, totalTh);
        });

        matrixBody.innerHTML = '';

        if (items.length === 0 || facilities.length === 0) {
            if (emptyMsg) emptyMsg.classList.remove('d-none');
            return;
        }
        if (emptyMsg) emptyMsg.classList.add('d-none');

        items.forEach(item => {
            const tr = document.createElement('tr');

            // Item name + batch
            const tdItem = document.createElement('td');
            tdItem.classList.add('text-start');
            tdItem.innerHTML = `<div>${escapeHtml(item.itemName)}</div><small class="text-muted">${escapeHtml(item.stockLabel)}</small>`;
            tr.appendChild(tdItem);

            // Available
            const tdAvail = document.createElement('td');
            tdAvail.textContent = item.available;
            tdAvail.classList.add('fw-semibold');
            tr.appendChild(tdAvail);

            // Facility quantity inputs
            let totalAllocated = 0;
            const inputCells = [];
            facilities.forEach(f => {
                const td = document.createElement('td');
                td.classList.add('js-facility-col');
                const input = document.createElement('input');
                input.type = 'number';
                input.min = '0';
                input.classList.add('form-control', 'form-control-sm', 'js-matrix-qty');
                input.name = `alloc_${item.formIndex}_${f.id}`;
                input.dataset.itemIndex = item.formIndex;
                input.dataset.facilityId = f.id;

                // Restore existing value
                const existingKey = `${item.formIndex}_${f.id}`;
                if (existingAllocations[existingKey]) {
                    input.value = existingAllocations[existingKey];
                    totalAllocated += existingAllocations[existingKey];
                } else {
                    input.value = '';
                }

                input.addEventListener('input', () => updateRowTotal(tr, item.available));
                td.appendChild(input);
                tr.appendChild(td);
                inputCells.push(input);
            });

            // Total column
            const tdTotal = document.createElement('td');
            tdTotal.classList.add('fw-semibold', 'js-row-total');
            tdTotal.textContent = totalAllocated || 0;
            tr.appendChild(tdTotal);

            matrixBody.appendChild(tr);
            updateRowTotal(tr, item.available);
        });
    }

    function updateRowTotal(tr, available) {
        const inputs = tr.querySelectorAll('.js-matrix-qty');
        let total = 0;
        inputs.forEach(input => {
            total += parseInt(input.value) || 0;
        });

        const totalCell = tr.querySelector('.js-row-total');
        if (totalCell) {
            totalCell.textContent = total;
            if (total > available) {
                totalCell.classList.add('text-danger');
                tr.classList.add('over-allocated');
            } else {
                totalCell.classList.remove('text-danger');
                tr.classList.remove('over-allocated');
            }
        }
    }

    // ────────────────────────────────────
    // Review building (Step 4)
    // ────────────────────────────────────

    function buildReview() {
        buildReviewHeader();
        buildReviewMatrix();
    }

    function buildReviewHeader() {
        const container = document.getElementById('review-header-content');
        if (!container) return;

        const title = document.getElementById('id_title');
        const tanggal = document.getElementById('id_allocation_date');
        const referensi = document.getElementById('id_referensi');
        const notes = document.getElementById('id_notes');
        const facilities = getSelectedFacilities();
        const staffChecked = document.querySelectorAll('#allocation-staff-list input[type="checkbox"]:checked');

        const staffNames = [];
        staffChecked.forEach(cb => {
            const label = cb.closest('.selection-picker-item');
            staffNames.push(getSelectionTitle(label, cb.value));
        });

        container.innerHTML = `
            <div class="row g-2 small">
                <div class="col-12"><strong>Judul:</strong> ${escapeHtml(title?.value || '—')}</div>
                <div class="col-md-4"><strong>Tanggal:</strong> ${escapeHtml(tanggal?.value || '—')}</div>
                <div class="col-md-4"><strong>Referensi:</strong> ${escapeHtml(referensi?.value || '—')}</div>
                <div class="col-md-6"><strong>Fasilitas:</strong> ${facilities.map(f => escapeHtml(f.name)).join(', ') || '—'}</div>
                <div class="col-md-6"><strong>Petugas:</strong> ${staffNames.map(n => escapeHtml(n)).join(', ') || '—'}</div>
                ${notes?.value ? `<div class="col-12"><strong>Catatan:</strong> ${escapeHtml(notes.value)}</div>` : ''}
            </div>
        `;
    }

    function buildReviewMatrix() {
        const container = document.getElementById('review-matrix-content');
        if (!container) return;

        const facilities = getSelectedFacilities();
        const items = getFormsetItems();

        if (items.length === 0 || facilities.length === 0) {
            container.innerHTML = '<div class="text-muted small">Tidak ada data untuk ditampilkan.</div>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm table-bordered alloc-matrix">';
        html += '<thead class="table-light"><tr><th>Barang</th><th>Tersedia</th>';
        facilities.forEach(f => { html += `<th>${escapeHtml(f.name)}</th>`; });
        html += '<th>Total</th></tr></thead><tbody>';

        items.forEach(item => {
            html += '<tr>';
            html += `<td class="text-start">${escapeHtml(item.itemName)}<br><small class="text-muted">${escapeHtml(item.stockLabel)}</small></td>`;
            html += `<td>${item.available}</td>`;

            let rowTotal = 0;
            facilities.forEach(f => {
                const input = document.querySelector(`input[name="alloc_${item.formIndex}_${f.id}"]`);
                const val = parseInt(input?.value) || 0;
                rowTotal += val;
                html += `<td>${val || '—'}</td>`;
            });

            const isOver = rowTotal > item.available;
            html += `<td class="fw-semibold ${isOver ? 'text-danger' : ''}">${rowTotal}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    // ────────────────────────────────────
    // Utility
    // ────────────────────────────────────

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});