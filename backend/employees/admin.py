from django.contrib import admin

from .models import AuditLog, Department, Employee


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_code",
        "first_name",
        "last_name",
        "email",
        "department",
        "position_title",
        "employment_status",
        "hire_date",
    )
    list_filter = ("employment_status", "department")
    search_fields = ("employee_code", "first_name", "last_name", "email", "position_title")
    actions = ("mark_as_suspended",)

    @admin.action(description="Suspend selected employees")
    def mark_as_suspended(self, request, queryset):
        updated = queryset.exclude(employment_status=Employee.EmploymentStatus.SUSPENDED).update(
            employment_status=Employee.EmploymentStatus.SUSPENDED
        )
        self.message_user(request, f"{updated} employee record(s) suspended.")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_username", "action_type", "target_table", "target_id", "source_ip")
    list_filter = ("action_type", "target_table")
    search_fields = ("actor_username", "target_table")
    readonly_fields = ("created_at",)
