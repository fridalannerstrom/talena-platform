from django.urls import path
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.urls import reverse_lazy
from .forms import TalenaPasswordResetForm, TalenaSetPasswordForm
from . import views
from apps.core import webhooks
from apps.activity import admin_views as activity_admin_views
from apps.activity import ai_statistics as activity_ai_statistics

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
    path(
        "password-reset/",
        PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            form_class=TalenaPasswordResetForm,
            email_template_name="accounts/emails/password_reset_email.txt",
            html_email_template_name="accounts/emails/password_reset_email.html",
            subject_template_name="accounts/emails/password_reset_subject.txt",
            success_url=reverse_lazy("core:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=TalenaSetPasswordForm,
            success_url=reverse_lazy("core:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("go/", post_login_redirect, name="post_login_redirect"),

    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin-activity/", activity_admin_views.platform_activity_log,
         name="admin_activity_log"),
    path("admin-activity/export/", activity_admin_views.platform_activity_export,
         name="admin_activity_export"),
    path("admin-ai-statistics/", activity_ai_statistics.platform_ai_statistics,
         name="admin_ai_statistics"),
    path("admin-ai-statistics/export/", activity_ai_statistics.platform_ai_statistics_export,
         name="admin_ai_statistics_export"),

    path("webhooks/sova/", sova_webhook, name="sova_webhook"),
    path("search/", views.global_search, name="global_search"),
    path(
        "activity/",
        views.customer_activity,
        name="customer_activity",
    ),
    path(
        "admin-ai-prompts/",
        views.admin_ai_prompts,
        name="admin_ai_prompts",
    ),
    path(
        "admin-ai-prompts/<str:key>/<str:language>/",
        views.admin_ai_prompt_edit,
        name="admin_ai_prompt_edit",
    ),
    path(
        "migration-onboarding/complete/",
        views.complete_migration_onboarding,
        name="complete_migration_onboarding",
    ),
]