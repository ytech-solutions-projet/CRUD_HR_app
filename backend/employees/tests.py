from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Department, Employee


class EmployeePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hr_admin_group = Group.objects.create(name="HR Admin")
        read_only_group = Group.objects.create(name="HR User")

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
        cls.read_only_user.groups.add(read_only_group)

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

    def test_hr_user_list_page_hides_management_actions(self):
        self.client.force_login(self.read_only_user)

        response = self.client.get(reverse("employee-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("employee-detail", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("employee-create"))
        self.assertNotContains(response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("employee-suspend", args=[self.employee.pk]))

    def test_hr_user_detail_page_hides_management_actions(self):
        self.client.force_login(self.read_only_user)

        response = self.client.get(reverse("employee-detail", args=[self.employee.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("employee-update", args=[self.employee.pk]))
        self.assertNotContains(response, reverse("employee-suspend", args=[self.employee.pk]))

    def test_hr_user_cannot_access_create_update_or_suspend_endpoints(self):
        self.client.force_login(self.read_only_user)

        create_response = self.client.get(reverse("employee-create"))
        update_response = self.client.get(reverse("employee-update", args=[self.employee.pk]))
        suspend_response = self.client.post(reverse("employee-suspend", args=[self.employee.pk]))

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)
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

    def test_hr_admin_create_provisions_employee_sign_in_account(self):
        self.client.force_login(self.hr_admin_user)

        response = self.client.post(
            reverse("employee-create"),
            {
                "employee_code": "YTHR-0101",
                "first_name": "Samir",
                "last_name": "Alaoui",
                "email": "samir.alaoui@ytech.local",
                "department": self.employee.department.pk,
                "position_title": "Analyst",
                "salary": "17500.00",
                "hire_date": "2024-02-01",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "account_password": "StartPass123!",
            },
        )

        self.assertRedirects(response, reverse("employee-list"))
        created_employee = Employee.objects.get(employee_code="YTHR-0101")
        self.assertIsNotNone(created_employee.user)
        self.assertEqual(created_employee.user.username, "samir.alaoui@ytech.local")
        self.assertTrue(created_employee.user.check_password("StartPass123!"))
