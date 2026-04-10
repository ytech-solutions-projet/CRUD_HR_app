from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Department, Employee, EmployeeSanction, HolidayRequest, WorkedHourLog
from .services import generate_employee_email


class EmployeePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hr_admin_group = Group.objects.create(name="HR Admin")
        hr_user_group = Group.objects.create(name="HR User")
        ceo_group = Group.objects.create(name="CEO")
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

        cls.ceo_user = User.objects.create_user(
            username="ceo",
            password="ChangeMe123!",
            is_staff=True,
        )
        cls.ceo_user.groups.add(ceo_group)

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
                "annual_leave_allowance": 18,
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
                "annual_leave_allowance": 18,
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
                "annual_leave_allowance": 24,
                "hire_date": "2024-01-15",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "account_password": "",
            },
        )

        self.assertRedirects(response, reverse("employee-list"))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.email, generate_employee_email("Nadia", "Bennani", self.employee))
        self.assertEqual(self.employee.user.username, self.employee.email)

    def test_first_review_approves_holiday_request(self):
        employee_user = User.objects.create_user(
            username="nadia.elidrissi@ytech.local",
            email="nadia.elidrissi@ytech.local",
            password="Welcome12345!",
        )
        self.employee.user = employee_user
        self.employee.save(update_fields=["user", "updated_at"])
        holiday_request = HolidayRequest.objects.create(
            employee=self.employee,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 4, 9),
            reason="Family commitment",
        )

        self.client.force_login(self.hr_admin_user)
        hr_response = self.client.post(
            reverse("holiday-request-review", args=[holiday_request.pk, "hr"]),
            {"decision": "approve"},
            follow=True,
        )

        self.assertRedirects(hr_response, reverse("employee-leave-queue"))
        holiday_request.refresh_from_db()
        self.assertEqual(holiday_request.hr_status, HolidayRequest.ReviewStatus.APPROVED)
        self.assertEqual(holiday_request.ceo_status, HolidayRequest.ReviewStatus.PENDING)
        self.assertEqual(holiday_request.overall_status, HolidayRequest.ReviewStatus.APPROVED)
        self.assertContains(hr_response, "Holiday request approved.")

        self.client.force_login(self.ceo_user)
        ceo_response = self.client.post(
            reverse("holiday-request-review", args=[holiday_request.pk, "ceo"]),
            {"decision": "approve"},
            follow=True,
        )

        self.assertRedirects(ceo_response, reverse("employee-leave-queue"))
        holiday_request.refresh_from_db()
        self.assertEqual(holiday_request.ceo_status, HolidayRequest.ReviewStatus.PENDING)
        self.assertEqual(holiday_request.overall_status, HolidayRequest.ReviewStatus.APPROVED)
        self.assertContains(ceo_response, "This holiday request has already been approved.")

    def test_hr_user_cannot_access_or_review_holiday_requests(self):
        holiday_request = HolidayRequest.objects.create(
            employee=self.employee,
            start_date=date(2026, 4, 16),
            end_date=date(2026, 4, 18),
            reason="Personal trip",
        )

        self.client.force_login(self.read_only_user)
        queue_response = self.client.get(reverse("employee-leave-queue"))
        review_response = self.client.post(
            reverse("holiday-request-review", args=[holiday_request.pk, "hr"]),
            {"decision": "approve"},
        )

        self.assertEqual(queue_response.status_code, 403)
        self.assertEqual(review_response.status_code, 403)
        holiday_request.refresh_from_db()
        self.assertEqual(holiday_request.hr_status, HolidayRequest.ReviewStatus.PENDING)

    def test_ceo_can_review_holiday_request_before_hr_approval(self):
        holiday_request = HolidayRequest.objects.create(
            employee=self.employee,
            start_date=date(2026, 4, 14),
            end_date=date(2026, 4, 15),
            reason="Travel",
        )

        self.client.force_login(self.ceo_user)
        queue_response = self.client.get(reverse("employee-leave-queue"))
        self.assertContains(queue_response, "Approve as CEO")
        self.assertContains(queue_response, "Reject as CEO")

        response = self.client.post(
            reverse("holiday-request-review", args=[holiday_request.pk, "ceo"]),
            {"decision": "approve"},
            follow=True,
        )

        self.assertRedirects(response, reverse("employee-leave-queue"))
        holiday_request.refresh_from_db()
        self.assertEqual(holiday_request.hr_status, HolidayRequest.ReviewStatus.PENDING)
        self.assertEqual(holiday_request.ceo_status, HolidayRequest.ReviewStatus.APPROVED)
        self.assertEqual(holiday_request.overall_status, HolidayRequest.ReviewStatus.APPROVED)
        self.assertContains(response, "Holiday request approved.")

    def test_hr_can_record_sanctions_and_surplus_hours(self):
        self.client.force_login(self.hr_admin_user)

        sanction_response = self.client.post(
            reverse("employee-sanction-create", args=[self.employee.pk]),
            {
                "sanction_type": EmployeeSanction.SanctionType.WARNING,
                "subject": "Missed deadline",
                "details": "Weekly report was delivered one day late.",
                "issued_on": "2026-03-14",
            },
        )
        hours_response = self.client.post(
            reverse("employee-worked-hours-create", args=[self.employee.pk]),
            {
                "work_date": "2026-03-18",
                "scheduled_hours": "8.00",
                "worked_hours": "10.50",
                "notes": "Release support",
            },
        )

        self.assertRedirects(sanction_response, reverse("employee-detail", args=[self.employee.pk]))
        self.assertRedirects(hours_response, reverse("employee-detail", args=[self.employee.pk]))
        self.assertTrue(
            EmployeeSanction.objects.filter(employee=self.employee, subject="Missed deadline").exists()
        )
        worked_hour_log = WorkedHourLog.objects.get(employee=self.employee, work_date=date(2026, 3, 18))
        self.assertEqual(worked_hour_log.surplus_hours, Decimal("2.50"))
        self.assertEqual(self.employee.get_total_surplus_hours(), Decimal("2.50"))
