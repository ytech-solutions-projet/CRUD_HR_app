from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditLog


def get_source_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        actor_username=user.get_username(),
        action_type=AuditLog.ActionType.LOGIN,
        target_table="auth",
        source_ip=get_source_ip(request),
        details={"event": "user_logged_in"},
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if not user:
        return
    AuditLog.objects.create(
        actor_username=user.get_username(),
        action_type=AuditLog.ActionType.LOGOUT,
        target_table="auth",
        source_ip=get_source_ip(request),
        details={"event": "user_logged_out"},
    )
