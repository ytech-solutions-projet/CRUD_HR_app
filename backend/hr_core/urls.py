from django.contrib import admin
from django.urls import include, path

from accounts.views import HomeRedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("employees/", include("employees.urls")),
    path("", HomeRedirectView.as_view(), name="home"),
]
