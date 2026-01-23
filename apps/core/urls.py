from django.urls import path
from .views import customer_dashboard, admin_dashboard, root_redirect, health
from . import views
from .webhooks import sova_webhook

urlpatterns = [
    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("", root_redirect, name="root"),
    path("health/", health, name="health"),
    path("webhooks/sova/", sova_webhook, name="sova_webhook"),
]