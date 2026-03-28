from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Department, Employee
from .services import generate_employee_email


class EmployeePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hr_admin_group = Group.objects.create(name="HR Admin")
        hr_user_group = Group.objects.create(name="HR User")
        it_admin_group = Group.objects.create(name="IT Admin")

        cls.hr_admin_user = User.objects.create_user(
            username="hradmin",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.hr_admin_user.groups.add(hr_admin_group)

        cls.read_only_user = User.objects.create_user(
            username="hruser",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.read_only_user.groups.add(hr_user_group)

        cls.it_admin_user = User.objects.create_user(
            username="itadmin",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.it_admin_user.groups.add(it_admin_group)

        department = Department.objects.create(name="Engineering")
        cls.employee = Employee.objects.create(
            employee_code="YTHR-0100",
            first_name="Nadia",
            last_name="El Idrissi",
            email="nadia.elidrissi@ytech.local",
            department=department,
            position_title="Platform Engineer",
            salary=Decimal("22000.00"),
            hire_date=date(2024, 1, 15),
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )

    def test_hr_user_list_page_allows_add_and_edit_but_not_suspend(self):
        self.client.force_login(self.read_only_user)

        response = self.client.get(reverse("employee-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("employee-detail", args=[self.employee.pk]))
        self.assertContains(response, reverse("employee-create"))
        self.assertContains(response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("employee-suspend", args=[self.employee.pk]))

    def test_hr_user_detail_page_allows_edit_but_not_suspend(self):
        self.client.force_login(self.read_only_user)

        response = self.client.get(reverse("employee-detail", args=[self.employee.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("employee-suspend", args=[self.employee.pk]))

    def test_hr_user_can_access_create_and_update_but_not_suspend_endpoints(self):
        self.client.force_login(self.read_only_user)

        create_response = self.client.get(reverse("employee-create"))
        update_response = self.client.get(reverse("employee-update", args=[self.employee.pk]))
        suspend_response = self.client.post(reverse("employee-suspend", args=[self.employee.pk]))

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(suspend_response.status_code, 403)

    def test_hr_admin_can_manage_employees(self):
        self.client.force_login(self.hr_admin_user)

        list_response = self.client.get(reverse("employee-list"))
        detail_response = self.client.get(reverse("employee-detail", args=[self.employee.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, reverse("employee-create"))
        self.assertContains(list_response, reverse("employee-update", args=[self.employee.pk]))
        self.assertContains(list_response, reverse("employee-suspend", args=[self.employee.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, reverse("employee-update", args=[self.employee.pk]))
        self.assertContains(detail_response, reverse("employee-suspend", args=[self.employee.pk]))

    def test_it_admin_can_add_and_edit_employee_accounts_but_not_suspend(self):
        self.client.force_login(self.it_admin_user)

        list_response = self.client.get(reverse("employee-list"))
        detail_response = self.client.get(reverse("employee-detail", args=[self.employee.pk]))
        create_response = self.client.get(reverse("employee-create"))
        update_response = self.client.get(reverse("employee-update", args=[self.employee.pk]))
        suspend_response = self.client.post(reverse("employee-suspend", args=[self.employee.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, reverse("employee-create"))
        self.assertContains(list_response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(list_response, reverse("employee-suspend", args=[self.employee.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(detail_response, reverse("employee-suspend", args=[self.employee.pk]))
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(suspend_response.status_code, 403)

    def test_hr_admin_create_provisions_employee_sign_in_account(self):
        self.client.force_login(self.hr_admin_user)

        response = self.client.post(
            reverse("employee-create"),
            {
                "first_name": "Samir",
                "last_name": "Alaoui",
                "department": self.employee.department.pk,
                "position_title": "Analyst",
                "salary": "17500.00",
                "hire_date": "2024-02-01",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "account_password": "StartPass123!",
            },
        )

        self.assertRedirects(response, reverse("employee-list"))
        created_employee = Employee.objects.get(email="alaoui.samir@ytech.local")
        self.assertIsNotNone(created_employee.user)
        self.assertEqual(created_employee.employee_code, "YTHR-0101")
        self.assertEqual(created_employee.user.username, "alaoui.samir@ytech.local")
        self.assertTrue(created_employee.user.check_password("StartPass123!"))

    def test_duplicate_generated_email_gets_incremented_suffix(self):
        self.client.force_login(self.hr_admin_user)
        Employee.objects.create(
            employee_code="YTHR-0101",
            first_name="Salma",
            last_name="Alaoui",
            email="alaoui.salma@ytech.local",
            department=self.employee.department,
            position_title="Recruiter",
            salary=Decimal("16500.00"),
            hire_date=date(2024, 2, 10),
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )

        response = self.client.post(
            reverse("employee-create"),
            {
                "first_name": "Salma",
                "last_name": "Alaoui",
                "department": self.employee.department.pk,
                "position_title": "Recruiter",
                "salary": "16500.00",
                "hire_date": "2024-02-10",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "account_password": "StartPass123!",
            },
        )

        self.assertRedirects(response, reverse("employee-list"))
        created_employee = Employee.objects.get(employee_code="YTHR-0102")
        self.assertEqual(created_employee.email, "alaoui.salma_1@ytech.local")

    def test_employee_update_regenerates_email_from_last_name_and_first_name(self):
        self.client.force_login(self.hr_admin_user)
        self.employee.user = User.objects.create_user(
            username=self.employee.email,
            email=self.employee.email,
            password="StartPass123!",
        )
        self.employee.save(update_fields=["user", "updated_at"])

        response = self.client.post(
            reverse("employee-update", args=[self.employee.pk]),
            {
                "first_name": "Nadia",
                "last_name": "Bennani",
                "department": self.employee.department.pk,
                "position_title": self.employee.position_title,
                "salary": "22000.00",
                "hire_date": "2024-01-15",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "account_password": "",
            },
        )

        self.assertRedirects(response, reverse("employee-list"))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.email, generate_employee_email("Nadia", "Bennani", self.employee))
        self.assertEqual(self.employee.user.username, self.employee.email)
