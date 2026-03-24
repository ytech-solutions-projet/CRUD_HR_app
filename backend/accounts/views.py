from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.generic import DetailView, RedirectView

from accounts.forms import EmailOrUsernameAuthenticationForm
from employees.access import user_can_view_employee_directory
from employees.models import Employee


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


class EmployeeSelfServiceView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = "accounts/employee_self_service.html"
    context_object_name = "employee"

    def get_object(self, queryset=None):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist as exc:
            raise PermissionDenied("This account is not linked to an employee profile.") from exc
