from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("settings/", views.portal_settings, name="settings"),
]
