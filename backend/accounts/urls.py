from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import (
    AccountDeleteView,
    AccountAccessListView,
    AccountAccessUpdateView,
    DatabaseOverviewView,
    EmailLoginView,
    EmployeeHolidayRequestCreateView,
    EmployeeSanctionListView,
    EmployeeSelfServiceView,
)

urlpatterns = [
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("password-change-done"),
        ),
        name="password-change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password-change-done",
    ),
    path("accounts/access/", AccountAccessListView.as_view(), name="account-access-list"),
    path("accounts/access/<int:pk>/", AccountAccessUpdateView.as_view(), name="account-access-update"),
    path("accounts/access/<int:pk>/delete/", AccountDeleteView.as_view(), name="account-access-delete"),
    path("database/", DatabaseOverviewView.as_view(), name="database-overview"),
    path("me/", EmployeeSelfServiceView.as_view(), name="employee-self-service"),
    path("me/holiday-request/", EmployeeHolidayRequestCreateView.as_view(), name="employee-holiday-request"),
    path("me/sanctions/", EmployeeSanctionListView.as_view(), name="employee-sanctions"),
]
