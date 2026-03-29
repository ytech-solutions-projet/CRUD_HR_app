from django.urls import path

from .views import (
    EmployeeCreateView,
    EmployeeDetailView,
    EmployeeListView,
    EmployeeSanctionCreateView,
    EmployeeSuspendView,
    EmployeeUpdateView,
    HolidayRequestQueueView,
    HolidayRequestReviewView,
    WorkedHourLogCreateView,
)

urlpatterns = [
    path("", EmployeeListView.as_view(), name="employee-list"),
    path("new/", EmployeeCreateView.as_view(), name="employee-create"),
    path("leave-requests/", HolidayRequestQueueView.as_view(), name="employee-leave-queue"),
    path("leave-requests/<int:pk>/<str:role>/review/", HolidayRequestReviewView.as_view(), name="holiday-request-review"),
    path("<int:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("<int:pk>/edit/", EmployeeUpdateView.as_view(), name="employee-update"),
    path("<int:pk>/sanctions/new/", EmployeeSanctionCreateView.as_view(), name="employee-sanction-create"),
    path("<int:pk>/worked-hours/new/", WorkedHourLogCreateView.as_view(), name="employee-worked-hours-create"),
    path("<int:pk>/suspend/", EmployeeSuspendView.as_view(), name="employee-suspend"),
]
