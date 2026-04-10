from django import forms
from django.db.models import Q
from accounts.forms import EmployeeAccountMixin

from .models import Department, Employee, EmployeeSanction, HolidayRequest, WorkedHourLog, calculate_business_days
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
            "annual_leave_allowance",
            "hire_date",
            "employment_status",
        ]
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_account_password_field()
        self.fields["annual_leave_allowance"].help_text = "Annual leave entitlement in working days."

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


class HolidayRequestForm(forms.ModelForm):
    class Meta:
        model = HolidayRequest
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "handover_notes",
            "emergency_contact",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 4}),
            "handover_notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "handover_notes": "Optional notes for the team covering your work while you are away.",
            "emergency_contact": "Optional phone number or contact person during the leave period.",
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if not self.employee or not start_date or not end_date:
            return cleaned_data

        if calculate_business_days(start_date, end_date) == 0:
            self.add_error(None, "The selected period must include at least one working day.")
            return cleaned_data

        overlapping_requests = self.employee.holiday_requests.exclude(
            Q(hr_status=HolidayRequest.ReviewStatus.REJECTED)
            | Q(ceo_status=HolidayRequest.ReviewStatus.REJECTED)
        ).filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if self.instance.pk:
            overlapping_requests = overlapping_requests.exclude(pk=self.instance.pk)

        if overlapping_requests.exists():
            self.add_error(
                None,
                "This leave period overlaps with another leave request that is still open or already approved.",
            )
        return cleaned_data


class EmployeeSanctionForm(forms.ModelForm):
    class Meta:
        model = EmployeeSanction
        fields = ["sanction_type", "subject", "details", "issued_on"]
        widgets = {
            "issued_on": forms.DateInput(attrs={"type": "date"}),
            "details": forms.Textarea(attrs={"rows": 4}),
        }


class WorkedHourLogForm(forms.ModelForm):
    class Meta:
        model = WorkedHourLog
        fields = ["work_date", "scheduled_hours", "worked_hours", "notes"]
        widgets = {
            "work_date": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "scheduled_hours": "Planned shift length for the day.",
            "worked_hours": "Total hours effectively worked that day.",
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee

    def clean(self):
        cleaned_data = super().clean()
        work_date = cleaned_data.get("work_date")
        if not self.employee or not work_date:
            return cleaned_data

        duplicate_logs = self.employee.worked_hour_logs.filter(work_date=work_date)
        if self.instance.pk:
            duplicate_logs = duplicate_logs.exclude(pk=self.instance.pk)
        if duplicate_logs.exists():
            self.add_error("work_date", "A worked-hours log already exists for this employee on that date.")
        return cleaned_data
