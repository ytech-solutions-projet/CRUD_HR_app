READ_GROUPS = {"HR User", "HR Admin", "IT Admin"}
WRITE_GROUPS = {"HR Admin"}
SUSPEND_GROUPS = WRITE_GROUPS


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
