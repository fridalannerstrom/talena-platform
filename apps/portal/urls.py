from django.urls import path
from . import views
from .views import PortalPasswordChangeView

app_name = "portal"

urlpatterns = [
    path("settings/", views.portal_settings, name="settings"),
    path("settings/password/", PortalPasswordChangeView.as_view(), name="password_change"),
]
