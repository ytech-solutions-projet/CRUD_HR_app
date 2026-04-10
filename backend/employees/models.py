from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def calculate_business_days(start_date: date, end_date: date) -> int:
    if start_date > end_date:
        return 0

    total_days = 0
    current_day = start_date
    while current_day <= end_date:
        if current_day.weekday() < 5:
            total_days += 1
        current_day += timedelta(days=1)
    return total_days


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        SUSPENDED = "SUSPENDED", "Suspended"
        TERMINATED = "TERMINATED", "Terminated"

    employee_code = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    position_title = models.CharField(max_length=120)
    salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    annual_leave_allowance = models.PositiveIntegerField(default=18)
    hire_date = models.DateField()
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["department", "employment_status"]),
        ]

    def __str__(self):
        return f"{self.employee_code} - {self.first_name} {self.last_name}"

    def get_leave_balance(self, year: int | None = None) -> dict[str, int]:
        target_year = year or timezone.localdate().year
        approved_days = 0
        requested_days = 0

        for request in self.holiday_requests.all():
            request_days = request.business_days_for_year(target_year)
            if request.overall_status == HolidayRequest.ReviewStatus.APPROVED:
                approved_days += request_days
            elif request.is_open:
                requested_days += request_days

        allowed_days = self.annual_leave_allowance
        owed_days = max(approved_days - allowed_days, 0)
        remaining_days = max(allowed_days - approved_days, 0)
        return {
            "year": target_year,
            "allowed_days": allowed_days,
            "approved_days": approved_days,
            "requested_days": requested_days,
            "owed_days": owed_days,
            "remaining_days": remaining_days,
        }

    def get_total_surplus_hours(self) -> Decimal:
        total = Decimal("0.00")
        for worked_hour_log in self.worked_hour_logs.all():
            total += worked_hour_log.surplus_hours
        return total.quantize(Decimal("0.01"))


class HolidayRequest(models.Model):
    class LeaveType(models.TextChoices):
        ANNUAL = "ANNUAL", "Annual Leave"
        SICK = "SICK", "Sick Leave"
        UNPAID = "UNPAID", "Unpaid Leave"
        PERSONAL = "PERSONAL", "Personal Leave"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="holiday_requests")
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.ANNUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    handover_notes = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    hr_status = models.CharField(
        max_length=12,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hr_reviewed_holiday_requests",
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
    ceo_status = models.CharField(
        max_length=12,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    ceo_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ceo_reviewed_holiday_requests",
    )
    ceo_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "created_at"]),
            models.Index(fields=["hr_status", "ceo_status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.employee} leave request {self.start_date} to {self.end_date}"

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after the start date."})

    @property
    def total_days(self) -> int:
        return calculate_business_days(self.start_date, self.end_date)

    @property
    def overall_status(self) -> str:
        if self.hr_status == self.ReviewStatus.REJECTED or self.ceo_status == self.ReviewStatus.REJECTED:
            return self.ReviewStatus.REJECTED
        if self.hr_status == self.ReviewStatus.APPROVED or self.ceo_status == self.ReviewStatus.APPROVED:
            return self.ReviewStatus.APPROVED
        return self.ReviewStatus.PENDING

    @property
    def is_open(self) -> bool:
        return self.overall_status == self.ReviewStatus.PENDING

    @classmethod
    def get_review_status_label(cls, status: str | None, unresolved_label: str = "Not reviewed") -> str:
        if status in {None, cls.ReviewStatus.PENDING}:
            return unresolved_label
        return dict(cls.ReviewStatus.choices).get(status, unresolved_label)

    @property
    def hr_status_label(self) -> str:
        return self.get_review_status_label(self.hr_status)

    @property
    def ceo_status_label(self) -> str:
        return self.get_review_status_label(self.ceo_status)

    @property
    def overall_status_label(self) -> str:
        return self.get_review_status_label(self.overall_status, unresolved_label="Open")

    def business_days_for_year(self, year: int) -> int:
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        effective_start = max(self.start_date, year_start)
        effective_end = min(self.end_date, year_end)
        if effective_start > effective_end:
            return 0
        return calculate_business_days(effective_start, effective_end)

    def apply_review(self, role: str, reviewer, decision: str):
        reviewed_at = timezone.now()
        if role == "hr":
            self.hr_status = decision
            self.hr_reviewed_by = reviewer
            self.hr_reviewed_at = reviewed_at
        elif role == "ceo":
            self.ceo_status = decision
            self.ceo_reviewed_by = reviewer
            self.ceo_reviewed_at = reviewed_at
        else:
            raise ValueError("Unsupported review role.")


class EmployeeSanction(models.Model):
    class SanctionType(models.TextChoices):
        WARNING = "WARNING", "Warning"
        BLAME = "BLAME", "Blame"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="sanctions")
    sanction_type = models.CharField(max_length=20, choices=SanctionType.choices)
    subject = models.CharField(max_length=150)
    details = models.TextField()
    issued_on = models.DateField(default=timezone.localdate)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_sanctions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_on", "-created_at"]
        indexes = [
            models.Index(fields=["employee", "issued_on"]),
            models.Index(fields=["sanction_type"]),
        ]

    def __str__(self):
        return f"{self.get_sanction_type_display()} for {self.employee}"


class WorkedHourLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="worked_hour_logs")
    work_date = models.DateField()
    scheduled_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("8.00"),
        validators=[MinValueValidator(0)],
    )
    worked_hours = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    notes = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_worked_hours",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-work_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "work_date"], name="unique_employee_work_date"),
        ]
        indexes = [
            models.Index(fields=["employee", "work_date"]),
        ]

    def __str__(self):
        return f"{self.employee} hours for {self.work_date}"

    @property
    def surplus_hours(self) -> Decimal:
        surplus = self.worked_hours - self.scheduled_hours
        if surplus < 0:
            return Decimal("0.00")
        return surplus.quantize(Decimal("0.01"))


class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        SUSPEND = "SUSPEND", "Suspend"
        DELETE = "DELETE", "Delete"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"

    actor_username = models.CharField(max_length=150)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    target_table = models.CharField(max_length=100)
    target_id = models.BigIntegerField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["actor_username"]),
        ]

    def __str__(self):
        return f"{self.action_type} by {self.actor_username} on {self.target_table}"
