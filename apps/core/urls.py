from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

from .views import (
    customer_dashboard,
    admin_dashboard,
    root_redirect,
    health,
    post_login_redirect,
)
from .webhooks import sova_webhook

app_name = "core"

urlpatterns = [
    path("", root_redirect, name="root"),
    path("health/", health, name="health"),

    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("go/", post_login_redirect, name="post_login_redirect"),

    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),

    path("webhooks/sova/", sova_webhook, name="sova_webhook"),
    path("search/", views.global_search, name="global_search"),
]