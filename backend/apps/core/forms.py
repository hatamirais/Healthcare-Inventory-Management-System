from django import forms
from .models import SystemSettings


REQUIRED_NUMBERING_TOKENS = ("{seq}", "{year}")

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            'platform_label',
            'facility_name',
            'facility_address',
            'facility_phone',
            'header_title',
            'lplpo_distribution_number_template',
            'special_request_distribution_number_template',
            'logo'
        ]
        labels = {
            'lplpo_distribution_number_template': 'Template nomor distribusi LPLPO',
            'special_request_distribution_number_template': 'Template nomor Permintaan Khusus',
        }
        widgets = {
            'facility_address': forms.Textarea(attrs={'rows': 3}),
            'lplpo_distribution_number_template': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'special_request_distribution_number_template': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
        }

    def clean_lplpo_distribution_number_template(self):
        return self._clean_numbering_template(
            'lplpo_distribution_number_template',
            'Template nomor LPLPO',
        )

    def clean_special_request_distribution_number_template(self):
        return self._clean_numbering_template(
            'special_request_distribution_number_template',
            'Template nomor Permintaan Khusus',
        )

    def _clean_numbering_template(self, field_name, label):
        value = (self.cleaned_data.get(field_name) or '').strip()
        if not value:
            raise forms.ValidationError(f'{label} wajib diisi.')

        missing_tokens = [token for token in REQUIRED_NUMBERING_TOKENS if token not in value]
        if missing_tokens:
            raise forms.ValidationError(
                f"{label} harus memuat placeholder {' dan '.join(missing_tokens)}."
            )

        for token in REQUIRED_NUMBERING_TOKENS:
            if value.count(token) != 1:
                raise forms.ValidationError(
                    f'{label} hanya boleh memakai placeholder {token} satu kali.'
                )

        normalized = value
        for token in REQUIRED_NUMBERING_TOKENS:
            normalized = normalized.replace(token, '')
        if '{' in normalized or '}' in normalized:
            raise forms.ValidationError(
                f'{label} hanya mendukung placeholder {{seq}} dan {{year}}.'
            )

        return value
