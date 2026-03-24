from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

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

        user_model = get_user_model()
        conflicts = user_model.objects.filter(
            Q(username__iexact=email) | Q(email__iexact=email)
        ).exclude(pk=self.instance.user_id)
        if conflicts.exists():
            self.add_error("email", "A sign-in account already uses this work email.")

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
