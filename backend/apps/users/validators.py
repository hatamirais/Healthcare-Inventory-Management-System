import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class StrongPasswordValidator:
    """
    Validate whether the password contains:
    - at least one uppercase letter
    - at least one lowercase letter
    - at least one number
    - at least one symbol/special character
    """
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password harus mengandung setidaknya satu huruf besar (A-Z)."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password harus mengandung setidaknya satu huruf kecil (a-z)."),
                code='password_no_lower',
            )
        if not re.search(r'\d', password):
            raise ValidationError(
                _("Password harus mengandung setidaknya satu angka (0-9)."),
                code='password_no_number',
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("Password harus mengandung setidaknya satu karakter spesial (contoh: @, #, $)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _(
            "Password harus memiliki huruf besar, huruf kecil, angka, dan karakter spesial."
        )
