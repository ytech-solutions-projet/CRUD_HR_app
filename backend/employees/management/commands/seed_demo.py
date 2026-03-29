from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from employees.models import Department, Employee, EmployeeSanction, HolidayRequest, WorkedHourLog
from employees.services import employee_sign_in_is_active


class Command(BaseCommand):
    help = "Create demo groups, users, departments, and employees for local development."

    def handle(self, *args, **options):
        hr_user_group, _ = Group.objects.get_or_create(name="HR User")
        hr_admin_group, _ = Group.objects.get_or_create(name="HR Admin")
        ceo_group, _ = Group.objects.get_or_create(name="CEO")
        it_admin_group, _ = Group.objects.get_or_create(name="IT Admin")

        departments = ["Human Resources", "Engineering", "Sales", "Finance"]
        created_departments = {}
        for name in departments:
            department, _ = Department.objects.get_or_create(name=name)
            created_departments[name] = department

        admin_user, created = User.objects.get_or_create(
            username="hradmin",
            defaults={
                "first_name": "HR",
                "last_name": "Admin",
                "email": "hradmin@ytech.local",
                "is_staff": True,
            },
        )
        if created or not admin_user.check_password("ChangeMe123!"):
            admin_user.set_password("ChangeMe123!")
            admin_user.is_staff = True
            admin_user.save()
        admin_user.groups.add(hr_admin_group)

        analyst_user, created = User.objects.get_or_create(
            username="hruser",
            defaults={
                "first_name": "HR",
                "last_name": "User",
                "email": "hruser@ytech.local",
                "is_staff": True,
            },
        )
        if created or not analyst_user.check_password("ChangeMe123!"):
            analyst_user.set_password("ChangeMe123!")
            analyst_user.is_staff = True
            analyst_user.save()
        analyst_user.groups.add(hr_user_group)

        auditor_user, created = User.objects.get_or_create(
            username="itadmin",
            defaults={
                "first_name": "IT",
                "last_name": "Admin",
                "email": "itadmin@ytech.local",
                "is_staff": True,
            },
        )
        if created or not auditor_user.check_password("ChangeMe123!"):
            auditor_user.set_password("ChangeMe123!")
            auditor_user.is_staff = True
            auditor_user.save()
        auditor_user.groups.add(it_admin_group)

        ceo_user, created = User.objects.get_or_create(
            username="ceo",
            defaults={
                "first_name": "Chief",
                "last_name": "Executive",
                "email": "ceo@ytech.local",
                "is_staff": True,
            },
        )
        if created or not ceo_user.check_password("ChangeMe123!"):
            ceo_user.set_password("ChangeMe123!")
            ceo_user.is_staff = True
            ceo_user.save()
        ceo_user.groups.add(ceo_group)

        sample_employees = [
            {
                "employee_code": "YTHR-0001",
                "first_name": "Sara",
                "last_name": "Bennani",
                "email": "sara.bennani@ytech.local",
                "department": created_departments["Human Resources"],
                "position_title": "HR Specialist",
                "salary": Decimal("14000.00"),
                "hire_date": date(2024, 5, 13),
                "employment_status": Employee.EmploymentStatus.ACTIVE,
            },
            {
                "employee_code": "YTHR-0002",
                "first_name": "Adam",
                "last_name": "Mouline",
                "email": "adam.mouline@ytech.local",
                "department": created_departments["Engineering"],
                "position_title": "Backend Engineer",
                "salary": Decimal("18500.00"),
                "hire_date": date(2023, 11, 1),
                "employment_status": Employee.EmploymentStatus.ACTIVE,
            },
            {
                "employee_code": "YTHR-0003",
                "first_name": "Lina",
                "last_name": "Tahiri",
                "email": "lina.tahiri@ytech.local",
                "department": created_departments["Finance"],
                "position_title": "Accountant",
                "salary": Decimal("15500.00"),
                "hire_date": date(2022, 9, 15),
                "employment_status": Employee.EmploymentStatus.ON_LEAVE,
            },
        ]

        for employee_payload in sample_employees:
            employee, _ = Employee.objects.update_or_create(
                employee_code=employee_payload["employee_code"],
                defaults=employee_payload,
            )
            employee_user, _ = User.objects.get_or_create(
                username=employee.email,
                defaults={
                    "email": employee.email,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "is_staff": False,
                    "is_active": employee_sign_in_is_active(employee),
                },
            )
            employee_user.email = employee.email
            employee_user.first_name = employee.first_name
            employee_user.last_name = employee.last_name
            employee_user.is_staff = False
            employee_user.is_active = employee_sign_in_is_active(employee)
            if not employee_user.check_password("WelcomeEmployee123!"):
                employee_user.set_password("WelcomeEmployee123!")
            employee_user.save()
            if employee.user_id != employee_user.pk:
                employee.user = employee_user
                employee.save(update_fields=["user", "updated_at"])

        sara = Employee.objects.get(employee_code="YTHR-0001")
        adam = Employee.objects.get(employee_code="YTHR-0002")

        HolidayRequest.objects.update_or_create(
            employee=adam,
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 10),
            defaults={
                "leave_type": HolidayRequest.LeaveType.ANNUAL,
                "reason": "Family travel",
                "handover_notes": "Shared deployment notes with the platform squad.",
                "emergency_contact": "+212600000000",
                "hr_status": HolidayRequest.ReviewStatus.APPROVED,
                "hr_reviewed_by": admin_user,
                "ceo_status": HolidayRequest.ReviewStatus.PENDING,
            },
        )

        EmployeeSanction.objects.update_or_create(
            employee=adam,
            subject="Late project handoff",
            defaults={
                "sanction_type": EmployeeSanction.SanctionType.WARNING,
                "details": "Project documentation was delivered after the agreed deadline.",
                "issued_on": date(2026, 2, 12),
                "issued_by": admin_user,
            },
        )

        WorkedHourLog.objects.update_or_create(
            employee=adam,
            work_date=date(2026, 3, 18),
            defaults={
                "scheduled_hours": Decimal("8.00"),
                "worked_hours": Decimal("10.50"),
                "notes": "Production release support.",
                "recorded_by": sara.user,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write("Users: hradmin / ChangeMe123!, hruser / ChangeMe123!, ceo / ChangeMe123!, itadmin / ChangeMe123!")
        self.stdout.write("Demo employees: sara.bennani@ytech.local / WelcomeEmployee123! (same password for seeded employees)")
