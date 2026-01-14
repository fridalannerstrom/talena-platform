from django.urls import path
from .views import customer_dashboard, admin_dashboard
from . import views

urlpatterns = [
    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
]