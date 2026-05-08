import re
from django.utils import timezone


def get_template_from_settings(field_name, default_template=None):
    """Retrieve a document-number template from SystemSettings or return default."""
    from apps.core.models import SystemSettings

    settings = SystemSettings.get_settings()
    return getattr(settings, field_name, None) or default_template


def _build_template_pattern(template):
    escaped_template = re.escape(template)
    escaped_template = escaped_template.replace(re.escape("{seq}"), r"(?P<sequence>\d+)")
    escaped_template = escaped_template.replace(re.escape("{year}"), r"(?P<year>\d{4})")
    return re.compile(rf"^{escaped_template}$")


def _render_document_number(template, sequence, year):
    return template.format(seq=sequence, year=year)


def render_document_number_preview(
    *,
    template=None,
    template_field_name=None,
    template_default=None,
    sequence="12",
    year=None,
):
    if template is None and template_field_name is None:
        return None
    if template is None and template_field_name:
        template = get_template_from_settings(template_field_name, template_default)
    if template is None:
        return None
    year = str(year or timezone.now().year)
    return _render_document_number(template, sequence, year)


def generate_document_number(
    model_class,
    *,
    template=None,
    template_field_name=None,
    template_default=None,
    filter_kwargs=None,
    year=None,
    fallback_prefix=None,
):
    """
    Generic document-number generator.

    - If a template (or template_field_name) is provided, find the next sequence
      by scanning existing `document_number` values on `model_class` filtered
      by `filter_kwargs`.
    - If no template is available, fall back to a time-based prefix (e.g.
      `PREFIX-YYYYMM-XXXXX`) and increment the trailing sequence.
    """
    # Resolve template
    if template is None and template_field_name:
        template = get_template_from_settings(template_field_name, template_default)

    # Template-based numbering
    if template:
        year = str(year or timezone.now().year)
        pattern = _build_template_pattern(template)
        matching_numbers = model_class.objects.filter(**(filter_kwargs or {})).values_list("document_number", flat=True)

        current_max = 0
        for document_number in matching_numbers:
            match = pattern.fullmatch(document_number or "")
            if not match:
                continue
            if match.group("year") != year:
                continue
            try:
                current_max = max(current_max, int(match.group("sequence")))
            except (TypeError, ValueError):
                continue

        next_sequence = current_max + 1
        return _render_document_number(template, next_sequence, year)

    # Fallback prefix-based numbering
    year_month = timezone.now().strftime("%Y%m")
    prefix = fallback_prefix or f"DOC-{year_month}"
    prefix_with_dash = f"{prefix}-"

    last = (
        model_class.objects.filter(document_number__startswith=prefix_with_dash)
        .order_by("-document_number")
        .first()
    )
    if last:
        try:
            sequence = int(last.document_number.split("-")[-1]) + 1
        except (TypeError, ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1

    return f"{prefix}-{str(sequence).zfill(5)}"
