from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .access import (
    HOLIDAY_REVIEW_GROUPS,
    HR_OPERATION_GROUPS,
    READ_GROUPS,
    SUSPEND_GROUPS,
    WRITE_GROUPS,
    user_can_manage_employees,
    user_can_manage_people_operations,
    user_can_review_holiday_as_ceo,
    user_can_review_holiday_as_hr,
    user_can_review_holiday_requests,
    user_has_group,
)
from .forms import EmployeeForm, EmployeeSanctionForm, EmployeeSearchForm, WorkedHourLogForm
from .models import AuditLog, Employee, HolidayRequest
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
    target_table: str | None = None,
    target_id: int | None = None,
):
    AuditLog.objects.create(
        actor_username=request.user.get_username() or "anonymous",
        action_type=action_type,
        target_table=target_table or ("employees" if employee else "auth"),
        target_id=target_id if target_id is not None else (employee.pk if employee else None),
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
        context["can_review_holiday_requests"] = user_can_review_holiday_requests(self.request.user)
        context["open_holiday_requests"] = HolidayRequest.objects.filter(
            hr_status=HolidayRequest.ReviewStatus.PENDING,
            ceo_status=HolidayRequest.ReviewStatus.PENDING,
        ).count()
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
        context["can_manage_people_operations"] = user_can_manage_people_operations(self.request.user)
        context["leave_balance"] = self.object.get_leave_balance()
        context["holiday_requests"] = self.object.holiday_requests.select_related(
            "hr_reviewed_by",
            "ceo_reviewed_by",
        )[:5]
        context["sanctions"] = self.object.sanctions.select_related("issued_by")[:5]
        context["worked_hour_logs"] = self.object.worked_hour_logs.select_related("recorded_by")[:5]
        context["total_surplus_hours"] = self.object.get_total_surplus_hours()
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


class HolidayRequestQueueView(GroupRequiredMixin, ListView):
    model = HolidayRequest
    template_name = "employees/holiday_request_queue.html"
    context_object_name = "holiday_requests"
    paginate_by = 20
    allowed_groups = HOLIDAY_REVIEW_GROUPS

    def get_queryset(self):
        return HolidayRequest.objects.select_related(
            "employee",
            "employee__department",
            "hr_reviewed_by",
            "ceo_reviewed_by",
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = HolidayRequest.objects.all()
        context["request_counts"] = {
            "open": all_requests.filter(
                hr_status=HolidayRequest.ReviewStatus.PENDING,
                ceo_status=HolidayRequest.ReviewStatus.PENDING,
            ).count(),
            "approved": all_requests.exclude(
                Q(hr_status=HolidayRequest.ReviewStatus.REJECTED)
                | Q(ceo_status=HolidayRequest.ReviewStatus.REJECTED)
            ).filter(
                Q(hr_status=HolidayRequest.ReviewStatus.APPROVED)
                | Q(ceo_status=HolidayRequest.ReviewStatus.APPROVED)
            ).count(),
            "rejected": all_requests.filter(
                Q(hr_status=HolidayRequest.ReviewStatus.REJECTED)
                | Q(ceo_status=HolidayRequest.ReviewStatus.REJECTED)
            ).count(),
        }
        context["can_review_as_hr"] = user_can_review_holiday_as_hr(self.request.user)
        context["can_review_as_ceo"] = user_can_review_holiday_as_ceo(self.request.user)
        return context


class HolidayRequestReviewView(GroupRequiredMixin, View):
    allowed_groups = HOLIDAY_REVIEW_GROUPS

    def post(self, request, *args, **kwargs):
        holiday_request = get_object_or_404(
            HolidayRequest.objects.select_related("employee"),
            pk=kwargs["pk"],
        )
        role = kwargs["role"]
        decision_key = request.POST.get("decision")
        if decision_key == "approve":
            decision = HolidayRequest.ReviewStatus.APPROVED
        elif decision_key == "reject":
            decision = HolidayRequest.ReviewStatus.REJECTED
        else:
            raise PermissionDenied("Unsupported review decision.")

        if role == "hr":
            if not user_can_review_holiday_as_hr(request.user):
                raise PermissionDenied("You do not have HR admin approval access.")
            current_status = holiday_request.hr_status
            update_fields = ["hr_status", "hr_reviewed_by", "hr_reviewed_at", "updated_at"]
        elif role == "ceo":
            if not user_can_review_holiday_as_ceo(request.user):
                raise PermissionDenied("You do not have CEO approval access.")
            current_status = holiday_request.ceo_status
            update_fields = ["ceo_status", "ceo_reviewed_by", "ceo_reviewed_at", "updated_at"]
        else:
            raise PermissionDenied("Unsupported review role.")

        if not holiday_request.is_open:
            if holiday_request.overall_status == HolidayRequest.ReviewStatus.REJECTED:
                messages.info(request, "This holiday request has already been rejected.")
            else:
                messages.info(request, "This holiday request has already been approved.")
            return redirect(request.POST.get("next") or reverse("employee-leave-queue"))

        if current_status != HolidayRequest.ReviewStatus.PENDING:
            messages.info(request, "This approval step has already been completed.")
            return redirect(request.POST.get("next") or reverse("employee-leave-queue"))

        holiday_request.apply_review(role, request.user, decision)
        holiday_request.save(update_fields=update_fields)
        log_audit_event(
            request,
            AuditLog.ActionType.UPDATE,
            holiday_request.employee,
            details={
                "holiday_request_id": holiday_request.pk,
                "employee_code": holiday_request.employee.employee_code,
                "review_role": role,
                "decision": decision,
            },
            target_table="holiday_request",
            target_id=holiday_request.pk,
        )

        if decision == HolidayRequest.ReviewStatus.REJECTED:
            messages.success(request, "Holiday request rejected.")
        else:
            messages.success(request, "Holiday request approved.")
        return redirect(request.POST.get("next") or reverse("employee-leave-queue"))


class EmployeeSanctionCreateView(GroupRequiredMixin, CreateView):
    form_class = EmployeeSanctionForm
    template_name = "employees/employee_sanction_form.html"
    allowed_groups = HR_OPERATION_GROUPS

    def dispatch(self, request, *args, **kwargs):
        self.employee = get_object_or_404(Employee, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["employee"] = self.employee
        return context

    def form_valid(self, form):
        sanction = form.save(commit=False)
        sanction.employee = self.employee
        sanction.issued_by = self.request.user
        sanction.save()
        log_audit_event(
            self.request,
            AuditLog.ActionType.CREATE,
            self.employee,
            details={
                "sanction_id": sanction.pk,
                "sanction_type": sanction.sanction_type,
                "employee_code": self.employee.employee_code,
            },
            target_table="employee_sanction",
            target_id=sanction.pk,
        )
        messages.success(self.request, "Warning or blame recorded successfully.")
        return HttpResponseRedirect(reverse("employee-detail", kwargs={"pk": self.employee.pk}))


class WorkedHourLogCreateView(GroupRequiredMixin, CreateView):
    form_class = WorkedHourLogForm
    template_name = "employees/worked_hour_log_form.html"
    allowed_groups = HR_OPERATION_GROUPS

    def dispatch(self, request, *args, **kwargs):
        self.employee = get_object_or_404(Employee, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["employee"] = self.employee
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["employee"] = self.employee
        return kwargs

    def form_valid(self, form):
        worked_hour_log = form.save(commit=False)
        worked_hour_log.employee = self.employee
        worked_hour_log.recorded_by = self.request.user
        worked_hour_log.save()
        log_audit_event(
            self.request,
            AuditLog.ActionType.CREATE,
            self.employee,
            details={
                "worked_hour_log_id": worked_hour_log.pk,
                "work_date": worked_hour_log.work_date.isoformat(),
                "surplus_hours": str(worked_hour_log.surplus_hours),
                "employee_code": self.employee.employee_code,
            },
            target_table="worked_hour_log",
            target_id=worked_hour_log.pk,
        )
        messages.success(self.request, "Worked hours recorded successfully.")
        return HttpResponseRedirect(reverse("employee-detail", kwargs={"pk": self.employee.pk}))
