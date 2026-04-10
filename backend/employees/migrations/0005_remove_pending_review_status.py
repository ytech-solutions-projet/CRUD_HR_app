from django.db import migrations


def normalize_open_statuses(apps, schema_editor):
    HolidayRequest = apps.get_model("employees", "HolidayRequest")
    HolidayRequest.objects.filter(hr_status__isnull=True).update(hr_status="PENDING")
    HolidayRequest.objects.filter(ceo_status__isnull=True).update(ceo_status="PENDING")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0004_employee_annual_leave_allowance_employeesanction_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_open_statuses, noop_reverse),
    ]
