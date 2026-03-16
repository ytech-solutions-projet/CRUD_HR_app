from django.core.validators import MinValueValidator
from django.db import models


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
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    position_title = models.CharField(max_length=120)
    salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
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
