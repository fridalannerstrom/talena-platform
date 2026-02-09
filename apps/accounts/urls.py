from django.urls import path
from . import views
from .views import AdminPasswordChangeView

app_name = "accounts"

urlpatterns = [
    # =========================================================================
    # USERS / CUSTOMERS (ADMIN)
    # =========================================================================
    path("customers/", views.admin_customers_list, name="admin_customers_list"),
    path("customers/new/", views.admin_customers_create, name="admin_customers_create"),

    # User detail (admin)
    path("users/<int:pk>/", views.admin_user_detail, name="admin_user_detail"),

    # =========================================================================
    # PROCESSES & CANDIDATES (ADMIN)
    # =========================================================================
    path("processes/<int:pk>/", views.admin_process_detail, name="admin_process_detail"),
    path(
        "processes/<int:process_pk>/candidates/<int:candidate_pk>/",
        views.admin_candidate_detail,
        name="admin_candidate_detail",
    ),

    # =========================================================================
    # INVITES (PUBLIC)
    # =========================================================================
    path("invite/accept/<uidb64>/<token>/", views.accept_invite, name="accept_invite"),
    path("invite/<uuid:invite_id>/", views.accept_invite_uuid, name="accept_invite_uuid"),

    # =========================================================================
    # ADMIN PROFILE
    # =========================================================================
    path("profile/", views.admin_profile, name="admin_profile"),
    path(
        "profile/password/",
        AdminPasswordChangeView.as_view(),
        name="admin_password_change",
    ),

    # =========================================================================
    # COMPANIES (ADMIN)
    # =========================================================================
    path("companies/", views.company_list, name="company_list"),
    path("companies/create/", views.company_create, name="company_create"),
    path("companies/<int:pk>/", views.company_detail, name="company_detail"),

    path(
        "companies/<int:company_pk>/members/<int:user_pk>/remove/",
        views.company_member_remove,
        name="company_member_remove",
    ),
    path(
        "companies/<int:company_pk>/members/<int:user_pk>/role/",
        views.company_member_update_role,
        name="company_member_update_role",
    ),
    path(
        "companies/<int:company_pk>/orgunits/move/",
        views.orgunit_move,
        name="orgunit_move",
    ),
    path("companies/<int:pk>/account-structure/", views.company_account_structure, name="company_account_structure"),
    path("companies/<int:pk>/user-access/", views.company_user_access, name="company_user_access"),

    # AJAX endpoints för user access (sparar direkt)
    path("companies/<int:company_pk>/user-access/set/", views.company_user_access_set, name="company_user_access_set"),
    path("companies/<int:company_pk>/user-access/state/", views.company_user_access_state, name="company_user_access_state"),
]
