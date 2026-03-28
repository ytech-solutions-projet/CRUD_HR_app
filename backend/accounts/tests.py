from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
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


class AccountPrivilegeManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr_admin_group = Group.objects.create(name="HR Admin")
        cls.hr_user_group = Group.objects.create(name="HR User")
        cls.it_admin_group = Group.objects.create(name="IT Admin")

        cls.hr_admin_user = User.objects.create_user(
            username="hradmin",
            email="hradmin@ytech.local",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.hr_admin_user.groups.add(cls.hr_admin_group)

        cls.it_admin_user = User.objects.create_user(
            username="itadmin",
            email="itadmin@ytech.local",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.it_admin_user.groups.add(cls.it_admin_group)

        cls.target_user = User.objects.create_user(
            username="samir.alaoui@ytech.local",
            email="samir.alaoui@ytech.local",
            password="StartPass123!",
            first_name="Samir",
            last_name="Alaoui",
            is_staff=False,
        )

    def test_hr_admin_can_open_account_access_pages(self):
        self.client.force_login(self.hr_admin_user)

        list_response = self.client.get(reverse("account-access-list"))
        edit_response = self.client.get(reverse("account-access-update", args=[self.target_user.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.target_user.username)
        self.assertContains(list_response, reverse("account-access-update", args=[self.target_user.pk]))
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, "Assigned privileges")

    def test_non_hr_admin_cannot_manage_account_privileges(self):
        self.client.force_login(self.it_admin_user)

        list_response = self.client.get(reverse("account-access-list"))
        edit_response = self.client.get(reverse("account-access-update", args=[self.target_user.pk]))

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(edit_response.status_code, 403)

    def test_hr_admin_can_view_database_overview(self):
        department = Department.objects.create(name="Finance")
        Employee.objects.create(
            employee_code="YTHR-9999",
            first_name="Lina",
            last_name="Tahiri",
            email="tahiri.lina@ytech.local",
            department=department,
            position_title="Analyst",
            salary=Decimal("12000.00"),
            hire_date=date(2024, 5, 1),
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.client.force_login(self.hr_admin_user)

        response = self.client.get(reverse("database-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Database Overview")
        self.assertContains(response, "tahiri.lina@ytech.local")
        self.assertContains(response, self.target_user.username)

    def test_non_hr_admin_cannot_view_database_overview(self):
        self.client.force_login(self.it_admin_user)

        response = self.client.get(reverse("database-overview"))

        self.assertEqual(response.status_code, 403)

    def test_hr_admin_can_assign_privileges_to_an_account(self):
        self.client.force_login(self.hr_admin_user)

        response = self.client.post(
            reverse("account-access-update", args=[self.target_user.pk]),
            {"privilege_groups": ["HR User", "IT Admin"]},
            follow=True,
        )

        self.assertRedirects(response, reverse("account-access-list"))
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_staff)
        self.assertCountEqual(
            self.target_user.groups.values_list("name", flat=True),
            ["HR User", "IT Admin"],
        )
        self.assertContains(response, "Account privileges updated successfully.")

    def test_hr_admin_cannot_remove_their_own_hr_admin_privilege(self):
        self.client.force_login(self.hr_admin_user)

        response = self.client.post(
            reverse("account-access-update", args=[self.hr_admin_user.pk]),
            {"privilege_groups": ["HR User"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Keep the HR Admin privilege on your own account so you do not remove your access.",
        )
        self.hr_admin_user.refresh_from_db()
        self.assertIn("HR Admin", self.hr_admin_user.groups.values_list("name", flat=True))
