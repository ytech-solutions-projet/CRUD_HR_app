from django.contrib import admin

from .models import AuditLog, Department, Employee, EmployeeSanction, HolidayRequest, WorkedHourLog


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


@admin.register(HolidayRequest)
class HolidayRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "hr_status",
        "ceo_status",
        "created_at",
    )
    list_filter = ("leave_type", "hr_status", "ceo_status")
    search_fields = ("employee__employee_code", "employee__first_name", "employee__last_name")


@admin.register(EmployeeSanction)
class EmployeeSanctionAdmin(admin.ModelAdmin):
    list_display = ("employee", "sanction_type", "subject", "issued_on", "issued_by")
    list_filter = ("sanction_type", "issued_on")
    search_fields = ("employee__employee_code", "employee__first_name", "employee__last_name", "subject")


@admin.register(WorkedHourLog)
class WorkedHourLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "work_date", "scheduled_hours", "worked_hours", "recorded_by")
    list_filter = ("work_date",)
    search_fields = ("employee__employee_code", "employee__first_name", "employee__last_name", "notes")
