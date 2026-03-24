from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .access import READ_GROUPS, SUSPEND_GROUPS, WRITE_GROUPS, user_can_manage_employees, user_has_group
from .forms import EmployeeForm, EmployeeSearchForm
from .models import AuditLog, Employee
from .services import sync_employee_sign_in_account


def get_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    request: HttpRequest,
    action_type: str,
    employee: Employee | None = None,
    details: dict | None = None,
):
    AuditLog.objects.create(
        actor_username=request.user.get_username() or "anonymous",
        action_type=action_type,
        target_table="employees" if employee else "auth",
        target_id=employee.pk if employee else None,
        source_ip=get_client_ip(request),
        details=details or {},
    )


class GroupRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_groups: set[str] = set()

    def test_func(self):
        return user_has_group(self.request.user, self.allowed_groups)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You do not have permission for this action.")
        return super().handle_no_permission()


class EmployeeListView(GroupRequiredMixin, ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    paginate_by = 10
    allowed_groups = READ_GROUPS

    def get_queryset(self):
        queryset = Employee.objects.select_related("department").all()
        self.search_form = EmployeeSearchForm(self.request.GET or None)
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q")
            department = self.search_form.cleaned_data.get("department")
            status = self.search_form.cleaned_data.get("employment_status")
            if query:
                queryset = queryset.filter(
                    Q(employee_code__icontains=query)
                    | Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(email__icontains=query)
                    | Q(position_title__icontains=query)
                )
            if department:
                queryset = queryset.filter(department=department)
            if status:
                queryset = queryset.filter(employment_status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = self.search_form
        context["status_counts"] = {
            "active": Employee.objects.filter(employment_status=Employee.EmploymentStatus.ACTIVE).count(),
            "on_leave": Employee.objects.filter(employment_status=Employee.EmploymentStatus.ON_LEAVE).count(),
            "suspended": Employee.objects.filter(employment_status=Employee.EmploymentStatus.SUSPENDED).count(),
            "terminated": Employee.objects.filter(employment_status=Employee.EmploymentStatus.TERMINATED).count(),
        }
        context["can_manage_employees"] = user_can_manage_employees(self.request.user)
        context["can_suspend"] = user_has_group(self.request.user, SUSPEND_GROUPS)
        return context


class EmployeeDetailView(GroupRequiredMixin, DetailView):
    model = Employee
    template_name = "employees/employee_detail.html"
    context_object_name = "employee"
    allowed_groups = READ_GROUPS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_employees"] = user_can_manage_employees(self.request.user)
        context["can_suspend"] = user_has_group(self.request.user, SUSPEND_GROUPS)
        return context


class EmployeeCreateView(GroupRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "employees/employee_form.html"
    success_url = reverse_lazy("employee-list")
    allowed_groups = WRITE_GROUPS

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            sync_employee_sign_in_account(self.object, form.cleaned_data.get("account_password"))
        log_audit_event(
            self.request,
            AuditLog.ActionType.CREATE,
            self.object,
            details={"employee_code": self.object.employee_code},
        )
        messages.success(
            self.request,
            "Employee added successfully. The employee can sign in with their work email and the password set on this form.",
        )
        return HttpResponseRedirect(self.get_success_url())


class EmployeeUpdateView(GroupRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "employees/employee_form.html"
    success_url = reverse_lazy("employee-list")
    allowed_groups = WRITE_GROUPS

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            sync_employee_sign_in_account(self.object, form.cleaned_data.get("account_password"))
        log_audit_event(
            self.request,
            AuditLog.ActionType.UPDATE,
            self.object,
            details={"employee_code": self.object.employee_code},
        )
        messages.success(
            self.request,
            "Employee updated successfully. The employee sign-in account is now synced to the current work email.",
        )
        return HttpResponseRedirect(self.get_success_url())


class EmployeeSuspendView(GroupRequiredMixin, DetailView):
    model = Employee
    template_name = "employees/employee_confirm_suspend.html"
    context_object_name = "employee"
    allowed_groups = SUSPEND_GROUPS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["already_suspended"] = self.object.employment_status == Employee.EmploymentStatus.SUSPENDED
        return context

    def post(self, request, *args, **kwargs):
        employee = self.get_object()
        if employee.employment_status == Employee.EmploymentStatus.SUSPENDED:
            messages.info(request, "Employee is already suspended.")
            return redirect("employee-detail", pk=employee.pk)

        previous_status = employee.employment_status
        employee.employment_status = Employee.EmploymentStatus.SUSPENDED
        employee.save(update_fields=["employment_status", "updated_at"])
        log_audit_event(
            request,
            AuditLog.ActionType.SUSPEND,
            employee,
            details={
                "employee_code": employee.employee_code,
                "previous_status": previous_status,
                "new_status": employee.employment_status,
            },
        )
        messages.success(request, "Employee suspended successfully.")
        return redirect("employee-detail", pk=employee.pk)
