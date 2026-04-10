PRIVILEGE_GROUP_DETAILS = {
    "HR User": "Can view, add, and edit employee records and sign-in accounts.",
    "HR Admin": "Full HR access, including suspending employees, reviewing holiday requests, and assigning privileges.",
    "CEO": "Executive access to review employee activity and decide holiday requests.",
    "IT Admin": "Can support account setup, assign account privileges, permanently delete sign-in accounts, and edit employee records without suspend access.",
}
PRIVILEGE_GROUP_ORDER = tuple(PRIVILEGE_GROUP_DETAILS)

READ_GROUPS = set(PRIVILEGE_GROUP_ORDER)
WRITE_GROUPS = {"HR User", "HR Admin", "IT Admin"}
SUSPEND_GROUPS = {"HR Admin"}
ACCOUNT_DIRECTORY_GROUPS = {"HR Admin", "IT Admin"}
ACCOUNT_PRIVILEGE_GROUPS = {"HR Admin", "IT Admin"}
ACCOUNT_DELETE_GROUPS = {"IT Admin"}
HR_REVIEW_GROUPS = {"HR User", "HR Admin"}
HOLIDAY_HR_REVIEW_GROUPS = {"HR Admin"}
CEO_REVIEW_GROUPS = {"CEO"}
HR_OPERATION_GROUPS = HR_REVIEW_GROUPS | CEO_REVIEW_GROUPS
HOLIDAY_REVIEW_GROUPS = HOLIDAY_HR_REVIEW_GROUPS | CEO_REVIEW_GROUPS


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


def user_can_access_account_directory(user) -> bool:
    return user_has_group(user, ACCOUNT_DIRECTORY_GROUPS)


def user_can_manage_account_privileges(user) -> bool:
    return user_has_group(user, ACCOUNT_PRIVILEGE_GROUPS)


def user_can_delete_accounts(user) -> bool:
    return user_has_group(user, ACCOUNT_DELETE_GROUPS)


def user_can_review_holiday_requests(user) -> bool:
    return user_has_group(user, HOLIDAY_REVIEW_GROUPS)


def user_can_review_holiday_as_hr(user) -> bool:
    return user_has_group(user, HOLIDAY_HR_REVIEW_GROUPS)


def user_can_review_holiday_as_ceo(user) -> bool:
    return user_has_group(user, CEO_REVIEW_GROUPS)


def user_can_manage_people_operations(user) -> bool:
    return user_has_group(user, HR_OPERATION_GROUPS)


def ensure_privilege_groups():
    from django.contrib.auth.models import Group

    for group_name in PRIVILEGE_GROUP_ORDER:
        Group.objects.get_or_create(name=group_name)
