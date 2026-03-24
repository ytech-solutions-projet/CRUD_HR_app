from django import forms
from accounts.forms import EmployeeAccountMixin

from .models import Department, Employee


class EmployeeForm(EmployeeAccountMixin, forms.ModelForm):
    account_password = forms.CharField(
        required=False,
        strip=False,
        label="Sign-in password",
        widget=forms.PasswordInput(render_value=True),
        help_text=(
            "Set the employee's starting sign-in password. "
            "They can change it themselves after logging in."
        ),
    )

    class Meta:
        model = Employee
        fields = [
            "employee_code",
            "first_name",
            "last_name",
            "email",
            "department",
            "position_title",
            "salary",
            "hire_date",
            "employment_status",
        ]
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_employee_code(self):
        return self.cleaned_data["employee_code"].strip().upper()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_account_password_field()

    def clean(self):
        cleaned_data = super().clean()
        self._validate_sign_in_account()
        return cleaned_data


class EmployeeSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False)
    employment_status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *Employee.EmploymentStatus.choices],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.order_by("name")
        self.fields["department"].empty_label = "All departments"
