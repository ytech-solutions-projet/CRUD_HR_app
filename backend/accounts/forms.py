from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from employees.access import PRIVILEGE_GROUP_DETAILS, PRIVILEGE_GROUP_ORDER, ensure_privilege_groups

class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Work email or username",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )


class EmployeeAccountMixin:
    def _validate_sign_in_account(self):
        email = self.cleaned_data.get("email")
        if not email:
            return

        employee_model = self._meta.model
        employee_conflicts = employee_model.objects.filter(email__iexact=email)
        if self.instance.pk:
            employee_conflicts = employee_conflicts.exclude(pk=self.instance.pk)

        user_model = get_user_model()
        account_conflicts = user_model.objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email)
        ).exclude(pk=self.instance.user_id)
        if employee_conflicts.exists() or account_conflicts.exists():
            self.add_error(
                "email" if "email" in self.fields else None,
                "This work email already exists. Use a different email address.",
            )
            return

        password = self.cleaned_data.get("account_password")
        needs_password = not self.instance.pk or self.instance.user_id is None
        if needs_password and not password:
            self.add_error("account_password", "Set a starting password so this employee can sign in.")
            return

        if password:
            provisional_user = self.instance.user or user_model(
                username=email,
                email=email,
                first_name=self.cleaned_data.get("first_name", ""),
                last_name=self.cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password, provisional_user)
            except ValidationError as exc:
                self.add_error("account_password", exc)

    def configure_account_password_field(self):
        if not self.instance.pk:
            self.fields["account_password"].required = True
            self.fields["account_password"].label = "Temporary sign-in password"
        elif self.instance.user_id is None:
            self.fields["account_password"].required = True
            self.fields["account_password"].label = "Create sign-in password"
            self.fields["account_password"].help_text = (
                "This employee does not have a sign-in account yet. "
                "Set a starting password to create one."
            )
        else:
            self.fields["account_password"].label = "Reset sign-in password"
            self.fields["account_password"].help_text = "Leave blank to keep the current password."


class AccountPrivilegeForm(forms.ModelForm):
    privilege_groups = forms.MultipleChoiceField(
        required=False,
        label="Assigned privileges",
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose which workspace privileges this account should receive.",
    )

    class Meta:
        model = get_user_model()
        fields = ()

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        ensure_privilege_groups()
        self.current_user = current_user
        self.fields["privilege_groups"].choices = [
            (group_name, group_name) for group_name in PRIVILEGE_GROUP_ORDER
        ]
        self.fields["privilege_groups"].initial = list(
            self.instance.groups.filter(name__in=PRIVILEGE_GROUP_ORDER).values_list("name", flat=True)
        )
        self.role_details = [
            (group_name, PRIVILEGE_GROUP_DETAILS[group_name]) for group_name in PRIVILEGE_GROUP_ORDER
        ]

    def clean_privilege_groups(self):
        selected_groups = set(self.cleaned_data.get("privilege_groups", []))
        if self.current_user and self.current_user.pk == self.instance.pk and "HR Admin" not in selected_groups:
            raise ValidationError(
                "Keep the HR Admin privilege on your own account so you do not remove your access."
            )
        return list(selected_groups)

    def save(self, commit=True):
        user = super().save(commit=False)
        selected_names = set(self.cleaned_data.get("privilege_groups", []))
        preserved_groups = list(user.groups.exclude(name__in=PRIVILEGE_GROUP_ORDER))
        selected_groups = {
            group.name: group for group in Group.objects.filter(name__in=selected_names)
        }

        user.is_staff = user.is_superuser or bool(selected_names)

        if commit:
            user.save(update_fields=["is_staff"])
            user.groups.set(
                preserved_groups
                + [selected_groups[group_name] for group_name in PRIVILEGE_GROUP_ORDER if group_name in selected_groups]
            )

        return user
