from django import forms
from accounts.forms import EmployeeAccountMixin

from .models import Department, Employee
from .services import generate_employee_code, generate_employee_email


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
            "first_name",
            "last_name",
            "department",
            "position_title",
            "salary",
            "hire_date",
            "employment_status",
        ]
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_account_password_field()

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")

        if first_name and last_name:
            try:
                generated_email = generate_employee_email(first_name, last_name, self.instance)
            except ValueError as exc:
                self.add_error(None, exc)
            else:
                cleaned_data["email"] = generated_email
                self.instance.email = generated_email
                if self.instance.pk:
                    cleaned_data["employee_code"] = self.instance.employee_code
                else:
                    generated_code = generate_employee_code()
                    cleaned_data["employee_code"] = generated_code
                    self.instance.employee_code = generated_code

        self._validate_sign_in_account()
        return cleaned_data

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.email = self.cleaned_data["email"]
        if not employee.employee_code:
            employee.employee_code = self.cleaned_data["employee_code"]
        if commit:
            employee.save()
        return employee


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
