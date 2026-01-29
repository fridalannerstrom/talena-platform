from django.urls import path
from . import views
from .views import AdminPasswordChangeView

app_name = "accounts"

urlpatterns = [
    # =========================================================================
    # CUSTOMER MANAGEMENT (befintligt)
    # =========================================================================
    path("customers/", views.admin_customers_list, name="admin_customers_list"),
    path("customers/new/", views.admin_customers_create, name="admin_customers_create"),
    
    # Customer detail (admin)
    path("users/<int:pk>/", views.admin_user_detail, name="admin_user_detail"),
    
    # Admin: Process detail
    path("processes/<int:pk>/", views.admin_process_detail, name="admin_process_detail"),
    path(
        "processes/<int:process_pk>/candidates/<int:candidate_pk>/",
        views.admin_candidate_detail,
        name="admin_candidate_detail",
    ),
    
    # Invite acceptance (public)
    path("invite/accept/<uidb64>/<token>/", views.accept_invite, name="accept_invite"),
    
    # Admin profile
    path("profile/", views.admin_profile, name="admin_profile"),
    path(
        "profile/password/",
        AdminPasswordChangeView.as_view(),
        name="admin_password_change",
    ),
    
    # =========================================================================
    # ACCOUNT HIERARCHY (NYTT!)
    # =========================================================================
    
    # Huvudvy för hierarkin
    path("hierarchy/", views.account_hierarchy, name="account_hierarchy"),
    
    # CRUD för accounts
    path("accounts/new/", views.account_create, name="account_create"),
    path("accounts/<int:parent_id>/new/", views.account_create, name="account_create_child"),
    path("accounts/<int:pk>/edit/", views.account_edit, name="account_edit"),
    path("accounts/<int:pk>/delete/", views.account_delete, name="account_delete"),
    
    # Hantera users per account
    path("accounts/<int:pk>/users/", views.account_users, name="account_users"),
    path("accounts/<int:pk>/users/<int:user_id>/remove/", views.account_user_remove, name="account_user_remove"),
]