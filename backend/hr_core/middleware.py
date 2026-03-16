from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


class LocalPreviewCsrfViewMiddleware(CsrfViewMiddleware):
    """
    Allow opaque-origin IDE previews in local development.

    Some embedded IDE browsers submit POST forms with `Origin: null`.
    We keep standard CSRF protection everywhere else and only relax the
    origin check when explicitly in debug mode for local hosts.
    """

    def _origin_verified(self, request):
        origin = request.META.get("HTTP_ORIGIN")
        host = request.get_host().split(":", 1)[0]
        if (
            getattr(settings, "DEBUG", False)
            and getattr(settings, "ALLOW_NULL_ORIGIN_IN_DEBUG", False)
            and origin == "null"
            and host in {"127.0.0.1", "localhost", "testserver"}
        ):
            return True
        return super()._origin_verified(request)
