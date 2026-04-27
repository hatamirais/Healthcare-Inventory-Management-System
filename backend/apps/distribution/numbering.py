import re

from django.utils import timezone


DOCUMENT_NUMBER_RULES = {
    "LPLPO": {
        "prefix": "440",
        "suffix": "SBBK.RF",
        "pattern": re.compile(r"^440/(?P<sequence>\d+)/SBBK\.RF/(?P<year>\d{4})$"),
    },
    "SPECIAL_REQUEST": {
        "prefix": "440",
        "suffix": "KD.F",
        "pattern": re.compile(r"^440/(?P<sequence>\d+)/KD\.F/(?P<year>\d{4})$"),
    },
}


def generate_distribution_document_number(model_class, distribution_type, year=None):
    rule = DOCUMENT_NUMBER_RULES.get(distribution_type)
    if rule is None:
        year_month = timezone.now().strftime("%Y%m")
        prefix = f"DIST-{year_month}"
        last = (
            model_class.objects.filter(document_number__startswith=f"{prefix}-")
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

    year = str(year or timezone.now().year)
    pattern = rule["pattern"]
    matching_numbers = model_class.objects.filter(
        distribution_type=distribution_type,
        document_number__endswith=f"/{year}",
    ).values_list("document_number", flat=True)

    current_max = 0
    for document_number in matching_numbers:
        match = pattern.fullmatch(document_number or "")
        if not match:
            continue
        current_max = max(current_max, int(match.group("sequence")))

    next_sequence = current_max + 1
    return f"{rule['prefix']}/{next_sequence}/{rule['suffix']}/{year}"