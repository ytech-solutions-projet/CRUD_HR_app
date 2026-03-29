from employees.access import (
    user_can_manage_account_privileges,
    user_can_review_holiday_requests,
    user_can_view_employee_directory,
)
from employees.models import Employee


def navigation(request):
    user = request.user
    if not user.is_authenticated:
        return {
            "can_access_employee_directory": False,
            "has_employee_self_service": False,
            "can_access_admin": False,
            "can_review_holiday_requests": False,
        }

    try:
        employee_profile = user.employee_profile
    except Employee.DoesNotExist:
        employee_profile = None

    return {
        "can_access_employee_directory": user_can_view_employee_directory(user),
        "can_manage_account_privileges": user_can_manage_account_privileges(user),
        "can_view_database": user_can_manage_account_privileges(user),
        "can_review_holiday_requests": user_can_review_holiday_requests(user),
        "has_employee_self_service": employee_profile is not None,
        "can_access_admin": user.is_staff,
    }
