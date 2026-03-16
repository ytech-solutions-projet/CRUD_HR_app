from django.urls import path

from .views import (
    EmployeeCreateView,
    EmployeeDetailView,
    EmployeeListView,
    EmployeeSuspendView,
    EmployeeUpdateView,
)

urlpatterns = [
    path("", EmployeeListView.as_view(), name="employee-list"),
    path("new/", EmployeeCreateView.as_view(), name="employee-create"),
    path("<int:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("<int:pk>/edit/", EmployeeUpdateView.as_view(), name="employee-update"),
    path("<int:pk>/suspend/", EmployeeSuspendView.as_view(), name="employee-suspend"),
]
