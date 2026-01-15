from django.urls import path
from .views import customer_dashboard, admin_dashboard
from . import views
from .views import root_redirect, health

urlpatterns = [
    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("", root_redirect, name="root"),
    path("health/", health, name="health"),
]