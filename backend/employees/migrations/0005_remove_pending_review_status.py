from django.db import migrations, models


def clear_pending_statuses(apps, schema_editor):
    HolidayRequest = apps.get_model("employees", "HolidayRequest")
    HolidayRequest.objects.filter(hr_status="PENDING").update(hr_status=None)
    HolidayRequest.objects.filter(ceo_status="PENDING").update(ceo_status=None)


def restore_pending_statuses(apps, schema_editor):
    HolidayRequest = apps.get_model("employees", "HolidayRequest")
    HolidayRequest.objects.filter(hr_status__isnull=True).update(hr_status="PENDING")
    HolidayRequest.objects.filter(ceo_status__isnull=True).update(ceo_status="PENDING")


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0004_employee_annual_leave_allowance_employeesanction_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="holidayrequest",
            name="hr_status",
            field=models.CharField(
                blank=True,
                choices=[("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                max_length=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="holidayrequest",
            name="ceo_status",
            field=models.CharField(
                blank=True,
                choices=[("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                max_length=12,
                null=True,
            ),
        ),
        migrations.RunPython(clear_pending_statuses, restore_pending_statuses),
    ]
