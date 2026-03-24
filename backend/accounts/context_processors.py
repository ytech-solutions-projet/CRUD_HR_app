from employees.access import user_can_view_employee_directory
from employees.models import Employee


def navigation(request):
    user = request.user
    if not user.is_authenticated:
        return {
            "can_access_employee_directory": False,
            "has_employee_self_service": False,
            "can_access_admin": False,
        }

    try:
        employee_profile = user.employee_profile
    except Employee.DoesNotExist:
        employee_profile = None

    return {
        "can_access_employee_directory": user_can_view_employee_directory(user),
        "has_employee_self_service": employee_profile is not None,
        "can_access_admin": user.is_staff,
    }
