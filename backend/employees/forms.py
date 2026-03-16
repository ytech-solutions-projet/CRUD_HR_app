from django import forms

from .models import Department, Employee


class EmployeeForm(forms.ModelForm):
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
