document.addEventListener('DOMContentLoaded', function () {
    var previewCard = document.getElementById('numbering-preview-card');
    var lplpoInput = document.getElementById('id_lplpo_distribution_number_template');
    var specialInput = document.getElementById('id_special_request_distribution_number_template');

    if (!previewCard || !lplpoInput || !specialInput) {
        return;
    }

    var sequence = previewCard.getAttribute('data-preview-sequence') || '12';
    var year = previewCard.getAttribute('data-preview-year') || String(new Date().getFullYear());

    function renderTemplate(template) {
        return (template || '').replaceAll('{seq}', sequence).replaceAll('{year}', year);
    }

    function updatePreview(title, value) {
        var templateEl = document.querySelector('[data-preview-template="' + title + '"]');
        var exampleEl = document.querySelector('[data-preview-example="' + title + '"]');

        if (templateEl) {
            templateEl.textContent = value;
        }
        if (exampleEl) {
            exampleEl.textContent = renderTemplate(value);
        }
    }

    function syncPreviews() {
        updatePreview('Preview LPLPO', lplpoInput.value);
        updatePreview('Preview Permintaan Khusus', specialInput.value);
    }

    lplpoInput.addEventListener('input', syncPreviews);
    specialInput.addEventListener('input', syncPreviews);

    syncPreviews();
});