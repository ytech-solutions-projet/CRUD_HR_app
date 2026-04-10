from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from employees.models import Department, Employee, EmployeeSanction, HolidayRequest, WorkedHourLog


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
        cls.employee_user = employee_user
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
        self.assertContains(response, "Employee Dashboard")
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

    def test_employee_can_submit_holiday_request_from_dashboard(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("employee-holiday-request"),
            {
                "leave_type": HolidayRequest.LeaveType.ANNUAL,
                "start_date": "2026-04-06",
                "end_date": "2026-04-08",
                "reason": "Family trip",
                "handover_notes": "Coverage shared with the support team.",
                "emergency_contact": "+212600000000",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("employee-self-service"))
        request = HolidayRequest.objects.get(employee=self.employee)
        self.assertEqual(request.hr_status, HolidayRequest.ReviewStatus.PENDING)
        self.assertEqual(request.ceo_status, HolidayRequest.ReviewStatus.PENDING)
        self.assertContains(
            response,
            "HR Admin and CEO can both review it, and the CEO can act without waiting for HR Admin.",
        )
        self.assertContains(response, "April 6, 2026 to April 8, 2026")

    def test_employee_can_view_warnings_and_surplus_hours(self):
        hr_user = User.objects.create_user(
            username="hradmin@ytech.local",
            email="hradmin@ytech.local",
            password="ChangeMe123!",
            is_staff=True,
        )
        EmployeeSanction.objects.create(
            employee=self.employee,
            sanction_type=EmployeeSanction.SanctionType.WARNING,
            subject="Late response to escalations",
            details="Two high-priority tickets were acknowledged after the SLA threshold.",
            issued_by=hr_user,
        )
        WorkedHourLog.objects.create(
            employee=self.employee,
            work_date=date(2026, 3, 20),
            scheduled_hours=Decimal("8.00"),
            worked_hours=Decimal("10.00"),
            recorded_by=hr_user,
        )

        self.client.force_login(self.employee_user)
        dashboard_response = self.client.get(reverse("employee-self-service"))
        sanctions_response = self.client.get(reverse("employee-sanctions"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Late response to escalations")
        self.assertContains(dashboard_response, "2.00")
        self.assertEqual(sanctions_response.status_code, 200)
        self.assertContains(sanctions_response, "Warnings and blames")
        self.assertContains(sanctions_response, "Late response to escalations")


class AccountPrivilegeManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr_admin_group = Group.objects.create(name="HR Admin")
        cls.hr_user_group = Group.objects.create(name="HR User")
        cls.ceo_group = Group.objects.create(name="CEO")
        cls.it_admin_group = Group.objects.create(name="IT Admin")
        cls.department = Department.objects.create(name="Security")

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
        cls.linked_employee = Employee.objects.create(
            employee_code="YTHR-0301",
            user=cls.target_user,
            first_name="Samir",
            last_name="Alaoui",
            email="samir.alaoui@ytech.local",
            department=cls.department,
            position_title="Security Analyst",
            salary=Decimal("14500.00"),
            hire_date=date(2024, 9, 2),
            employment_status=Employee.EmploymentStatus.ACTIVE,
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
        self.assertContains(edit_response, "CEO")

    def test_it_admin_can_open_account_access_pages(self):
        self.client.force_login(self.it_admin_user)

        list_response = self.client.get(reverse("account-access-list"))
        edit_response = self.client.get(reverse("account-access-update", args=[self.target_user.pk]))
        delete_response = self.client.get(reverse("account-access-delete", args=[self.target_user.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, reverse("account-access-delete", args=[self.target_user.pk]))
        self.assertContains(list_response, reverse("account-access-update", args=[self.target_user.pk]))
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, "Assigned privileges")
        self.assertEqual(delete_response.status_code, 200)

    def test_database_overview_is_disabled_for_privileged_users(self):
        self.client.force_login(self.hr_admin_user)

        hr_response = self.client.get(reverse("database-overview"))
        self.assertEqual(hr_response.status_code, 403)

        self.client.force_login(self.it_admin_user)
        it_response = self.client.get(reverse("database-overview"))
        self.assertEqual(it_response.status_code, 403)

    def test_navigation_hides_database_and_admin_links(self):
        self.client.force_login(self.it_admin_user)

        response = self.client.get(reverse("account-access-list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("database-overview"))
        self.assertNotContains(response, "/admin/")

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

    def test_it_admin_can_assign_privileges_to_an_account(self):
        self.client.force_login(self.it_admin_user)

        response = self.client.post(
            reverse("account-access-update", args=[self.target_user.pk]),
            {"privilege_groups": ["CEO"]},
            follow=True,
        )

        self.assertRedirects(response, reverse("account-access-list"))
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_staff)
        self.assertCountEqual(self.target_user.groups.values_list("name", flat=True), ["CEO"])
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

    def test_it_admin_can_delete_account_completely(self):
        self.client.force_login(self.it_admin_user)

        response = self.client.post(
            reverse("account-access-delete", args=[self.target_user.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("account-access-list"))
        self.assertFalse(User.objects.filter(pk=self.target_user.pk).exists())
        self.linked_employee.refresh_from_db()
        self.assertIsNone(self.linked_employee.user)
        self.assertContains(response, "Account deleted permanently. The linked employee profile was kept.")

    def test_it_admin_cannot_delete_their_own_account(self):
        self.client.force_login(self.it_admin_user)

        response = self.client.post(
            reverse("account-access-delete", args=[self.it_admin_user.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("account-access-list"))
        self.assertTrue(User.objects.filter(pk=self.it_admin_user.pk).exists())
        self.assertContains(response, "You cannot delete your own account while signed in.")
