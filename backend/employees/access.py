PRIVILEGE_GROUP_DETAILS = {
    "HR User": "Can view, add, and edit employee records and sign-in accounts.",
    "HR Admin": "Full HR access, including suspending employees and assigning privileges.",
    "IT Admin": "Can support account setup and edit employee records, without suspend access.",
}
PRIVILEGE_GROUP_ORDER = tuple(PRIVILEGE_GROUP_DETAILS)

READ_GROUPS = set(PRIVILEGE_GROUP_ORDER)
WRITE_GROUPS = set(PRIVILEGE_GROUP_ORDER)
SUSPEND_GROUPS = {"HR Admin"}
ACCOUNT_PRIVILEGE_GROUPS = {"HR Admin"}


def user_has_group(user, groups: set[str]) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=groups).exists()


def user_can_manage_employees(user) -> bool:
    return user_has_group(user, WRITE_GROUPS)


def user_can_view_employee_directory(user) -> bool:
    return user_has_group(user, READ_GROUPS)


def user_can_manage_account_privileges(user) -> bool:
    return user_has_group(user, ACCOUNT_PRIVILEGE_GROUPS)


def ensure_privilege_groups():
    from django.contrib.auth.models import Group

    for group_name in PRIVILEGE_GROUP_ORDER:
        Group.objects.get_or_create(name=group_name)
