from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, RedirectView, TemplateView, UpdateView

from accounts.forms import AccountPrivilegeForm, EmailOrUsernameAuthenticationForm
from employees.access import (
    PRIVILEGE_GROUP_DETAILS,
    PRIVILEGE_GROUP_ORDER,
    ensure_privilege_groups,
    user_can_manage_account_privileges,
    user_can_view_employee_directory,
)
from employees.forms import HolidayRequestForm
from employees.models import AuditLog, Department, Employee, HolidayRequest


def get_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_account_access_update(request: HttpRequest, target_user):
    AuditLog.objects.create(
        actor_username=request.user.get_username() or "anonymous",
        action_type=AuditLog.ActionType.UPDATE,
        target_table="auth_user",
        target_id=target_user.pk,
        source_ip=get_client_ip(request),
        details={
            "target_username": target_user.get_username(),
            "privileges": list(
                target_user.groups.filter(name__in=PRIVILEGE_GROUP_ORDER).values_list("name", flat=True)
            ),
        },
    )


def log_employee_self_service_event(
    request: HttpRequest,
    action_type: str,
    employee: Employee,
    target_table: str,
    target_id: int,
    details: dict | None = None,
):
    AuditLog.objects.create(
        actor_username=request.user.get_username() or "anonymous",
        action_type=action_type,
        target_table=target_table,
        target_id=target_id,
        source_ip=get_client_ip(request),
        details={"employee_code": employee.employee_code, **(details or {})},
    )


class AccountPrivilegeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return user_can_manage_account_privileges(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You do not have permission to manage account privileges.")
        return super().handle_no_permission()


class EmailLoginView(LoginView):
    authentication_form = EmailOrUsernameAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("home")


class HomeRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return reverse("login")
        if user_can_view_employee_directory(user):
            return reverse("employee-list")
        try:
            user.employee_profile
        except Employee.DoesNotExist as exc:
            raise PermissionDenied("No workspace is assigned to this account.") from exc
        return reverse("employee-self-service")


class AccountAccessListView(AccountPrivilegeRequiredMixin, ListView):
    model = get_user_model()
    template_name = "accounts/account_access_list.html"
    context_object_name = "account_rows"
    paginate_by = 20

    def get_queryset(self):
        ensure_privilege_groups()
        user_model = get_user_model()
        return user_model.objects.prefetch_related("groups").order_by("username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_details"] = [
            (group_name, PRIVILEGE_GROUP_DETAILS[group_name]) for group_name in PRIVILEGE_GROUP_ORDER
        ]
        context["account_rows"] = [
            {
                "user": account,
                "privileges": [
                    group.name
                    for group in account.groups.all()
                    if group.name in PRIVILEGE_GROUP_DETAILS
                ],
            }
            for account in context["account_rows"]
        ]
        return context


class AccountAccessUpdateView(AccountPrivilegeRequiredMixin, UpdateView):
    model = get_user_model()
    form_class = AccountPrivilegeForm
    template_name = "accounts/account_access_form.html"
    context_object_name = "account"
    success_url = reverse_lazy("account-access-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["current_user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_details"] = self.get_form().role_details
        try:
            linked_employee = self.object.employee_profile
        except Employee.DoesNotExist:
            linked_employee = None
        context["linked_employee"] = linked_employee
        return context

    def form_valid(self, form):
        self.object = form.save()
        log_account_access_update(self.request, self.object)
        messages.success(self.request, "Account privileges updated successfully.")
        return HttpResponseRedirect(self.get_success_url())


class DatabaseOverviewView(AccountPrivilegeRequiredMixin, TemplateView):
    template_name = "accounts/database_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_model = get_user_model()
        default_connection = connections["default"]
        database_settings = default_connection.settings_dict

        accounts = list(user_model.objects.prefetch_related("groups").order_by("username")[:20])
        context["database_summary"] = {
            "engine": database_settings.get("ENGINE", ""),
            "name": str(database_settings.get("NAME", "")),
            "host": database_settings.get("HOST") or "local file",
            "port": database_settings.get("PORT") or "-",
        }
        context["table_counts"] = {
            "departments": Department.objects.count(),
            "employees": Employee.objects.count(),
            "accounts": user_model.objects.count(),
            "groups": Group.objects.count(),
            "audit_logs": AuditLog.objects.count(),
        }
        context["departments"] = Department.objects.order_by("name")
        context["employees"] = Employee.objects.select_related("department", "user").order_by("last_name", "first_name")[:20]
        context["accounts"] = [
            {
                "user": account,
                "privileges": list(
                    account.groups.filter(name__in=PRIVILEGE_GROUP_ORDER).values_list("name", flat=True)
                ),
            }
            for account in accounts
        ]
        context["audit_logs"] = AuditLog.objects.order_by("-created_at")[:20]
        return context


class EmployeeSelfServiceView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = "accounts/employee_self_service.html"
    context_object_name = "employee"

    def get_object(self, queryset=None):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist as exc:
            raise PermissionDenied("This account is not linked to an employee profile.") from exc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leave_balance"] = self.object.get_leave_balance()
        context["holiday_requests"] = self.object.holiday_requests.select_related(
            "hr_reviewed_by",
            "ceo_reviewed_by",
        )[:10]
        context["sanctions"] = self.object.sanctions.select_related("issued_by")[:5]
        context["worked_hour_logs"] = self.object.worked_hour_logs.select_related("recorded_by")[:10]
        context["total_surplus_hours"] = self.object.get_total_surplus_hours()
        context["pending_holiday_requests_count"] = sum(
            1
            for holiday_request in self.object.holiday_requests.all()
            if holiday_request.overall_status == HolidayRequest.ReviewStatus.PENDING
        )
        return context


class EmployeeHolidayRequestCreateView(LoginRequiredMixin, CreateView):
    form_class = HolidayRequestForm
    template_name = "accounts/holiday_request_form.html"

    def get_employee(self):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist as exc:
            raise PermissionDenied("This account is not linked to an employee profile.") from exc

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["employee"] = self.get_employee()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_employee()
        context["employee"] = employee
        context["leave_balance"] = employee.get_leave_balance()
        return context

    def form_valid(self, form):
        employee = self.get_employee()
        holiday_request = form.save(commit=False)
        holiday_request.employee = employee
        holiday_request.save()
        log_employee_self_service_event(
            self.request,
            AuditLog.ActionType.CREATE,
            employee,
            target_table="holiday_request",
            target_id=holiday_request.pk,
            details={
                "leave_type": holiday_request.leave_type,
                "start_date": holiday_request.start_date.isoformat(),
                "end_date": holiday_request.end_date.isoformat(),
                "total_days": holiday_request.total_days,
            },
        )
        messages.success(
            self.request,
            "Holiday request submitted. It is now waiting for HR and CEO approval.",
        )
        return HttpResponseRedirect(reverse("employee-self-service"))


class EmployeeSanctionListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = "accounts/employee_sanction_list.html"
    context_object_name = "sanctions"

    def get_employee(self):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist as exc:
            raise PermissionDenied("This account is not linked to an employee profile.") from exc

    def get_queryset(self):
        return self.get_employee().sanctions.select_related("issued_by").all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_employee()
        context["employee"] = employee
        context["warning_count"] = employee.sanctions.filter(
            sanction_type="WARNING",
        ).count()
        context["blame_count"] = employee.sanctions.filter(
            sanction_type="BLAME",
        ).count()
        return context
