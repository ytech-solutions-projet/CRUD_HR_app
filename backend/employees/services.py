import re
import unicodedata

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Employee


ACTIVE_SIGN_IN_STATUSES = {
    Employee.EmploymentStatus.ACTIVE,
    Employee.EmploymentStatus.ON_LEAVE,
}
EMPLOYEE_CODE_PREFIX = "YTHR-"
WORK_EMAIL_DOMAIN = "@ytech.local"
EMPLOYEE_CODE_PATTERN = re.compile(rf"^{EMPLOYEE_CODE_PREFIX}(?P<number>\d+)$")


def employee_sign_in_is_active(employee: Employee) -> bool:
    return employee.employment_status in ACTIVE_SIGN_IN_STATUSES


def normalize_employee_name_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    if not normalized:
        raise ValueError("First name and last name must contain letters or numbers.")
    return normalized


def generate_employee_code() -> str:
    next_number = 1
    existing_codes = Employee.objects.values_list("employee_code", flat=True)
    for employee_code in existing_codes:
        match = EMPLOYEE_CODE_PATTERN.match(employee_code)
        if not match:
            continue
        next_number = max(next_number, int(match.group("number")) + 1)
    return f"{EMPLOYEE_CODE_PREFIX}{next_number:04d}"


def build_employee_email_local_part(first_name: str, last_name: str) -> str:
    normalized_first_name = normalize_employee_name_part(first_name)
    normalized_last_name = normalize_employee_name_part(last_name)
    return f"{normalized_last_name}.{normalized_first_name}"


def employee_email_exists(email: str, employee: Employee | None = None) -> bool:
    employee_conflicts = Employee.objects.filter(email__iexact=email)
    user_model = get_user_model()
    user_conflicts = user_model.objects.filter(
        Q(username__iexact=email) | Q(email__iexact=email)
    )

    if employee and employee.pk:
        employee_conflicts = employee_conflicts.exclude(pk=employee.pk)
    if employee and employee.user_id:
        user_conflicts = user_conflicts.exclude(pk=employee.user_id)

    return employee_conflicts.exists() or user_conflicts.exists()


def generate_employee_email(first_name: str, last_name: str, employee: Employee | None = None) -> str:
    base_local_part = build_employee_email_local_part(first_name, last_name)
    suffix = 0

    while True:
        suffix_part = f"_{suffix}" if suffix else ""
        candidate = f"{base_local_part}{suffix_part}{WORK_EMAIL_DOMAIN}"
        if not employee_email_exists(candidate, employee):
            return candidate
        suffix += 1


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
