from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "employees"
    verbose_name = "HR Employees"

    def ready(self):
        from . import signals  # noqa: F401
