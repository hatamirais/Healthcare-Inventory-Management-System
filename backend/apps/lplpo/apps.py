from django.apps import AppConfig


class LplpoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lplpo"
    verbose_name = "LPLPO"

    def ready(self):
        import apps.lplpo.signals  # noqa: F401
