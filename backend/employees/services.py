from django.contrib.auth import get_user_model

from .models import Employee


ACTIVE_SIGN_IN_STATUSES = {
    Employee.EmploymentStatus.ACTIVE,
    Employee.EmploymentStatus.ON_LEAVE,
}


def employee_sign_in_is_active(employee: Employee) -> bool:
    return employee.employment_status in ACTIVE_SIGN_IN_STATUSES


def sync_employee_sign_in_account(employee: Employee, password: str | None = None):
    user_model = get_user_model()
    user = employee.user or user_model()
    normalized_email = employee.email.strip().lower()

    user.username = normalized_email
    user.email = normalized_email
    user.first_name = employee.first_name
    user.last_name = employee.last_name
    user.is_staff = False
    user.is_active = employee_sign_in_is_active(employee)

    if password:
        user.set_password(password)
    elif user.pk is None:
        user.set_unusable_password()

    user.save()

    if employee.user_id != user.pk:
        employee.user = user
        employee.save(update_fields=["user", "updated_at"])

    return user
