from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from employees.models import Department, Employee


class EmployeeSelfServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="Support")
        employee_user = User.objects.create_user(
            username="noor.elamrani@ytech.local",
            email="noor.elamrani@ytech.local",
            password="Welcome12345!",
            first_name="Noor",
            last_name="El Amrani",
            is_staff=False,
        )
        cls.employee = Employee.objects.create(
            employee_code="YTHR-0300",
            user=employee_user,
            first_name="Noor",
            last_name="El Amrani",
            email="noor.elamrani@ytech.local",
            department=department,
            position_title="Support Specialist",
            salary=Decimal("12500.00"),
            hire_date=date(2024, 3, 11),
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )

    def test_employee_can_sign_in_with_work_email(self):
        response = self.client.post(
            reverse("login"),
            {"username": "noor.elamrani@ytech.local", "password": "Welcome12345!"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee Self Service")
        self.assertContains(response, reverse("password-change"))

    def test_employee_can_change_password(self):
        self.assertTrue(
            self.client.login(username="noor.elamrani@ytech.local", password="Welcome12345!")
        )

        response = self.client.post(
            reverse("password-change"),
            {
                "old_password": "Welcome12345!",
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("password-change-done"))
        self.client.logout()
        self.assertFalse(
            self.client.login(username="noor.elamrani@ytech.local", password="Welcome12345!")
        )
        self.assertTrue(
            self.client.login(username="noor.elamrani@ytech.local", password="NewStrongPass123!")
        )
