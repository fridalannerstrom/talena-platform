from django.urls import path
from . import views

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

    path("companies/<int:pk>/users/", views.company_users, name="company_users"),
    path("companies/<int:pk>/stats/", views.company_stats, name="company_stats"),
    path(
    "users/<int:user_pk>/processes/new/",
    views.admin_process_create_for_user,
    name="admin_process_create_for_user",
    ),
    path("processes/<int:pk>/edit/", views.admin_process_update, name="admin_process_update"),
    path("processes/<int:pk>/", views.admin_process_detail, name="admin_process_detail"),
    path("processes/<int:pk>/send-tests/", views.admin_process_send_tests, name="admin_process_send_tests"),
    path("processes/<int:process_id>/remove/<int:candidate_id>/", views.admin_remove_candidate_from_process, name="admin_remove_candidate_from_process"),
    path("processes/<int:pk>/statuses/", views.admin_process_invitation_statuses, name="admin_process_invitation_statuses"),
    path(
    "processes/<int:pk>/add-candidate/",
    views.admin_process_add_candidate,
    name="admin_process_add_candidate"
),
path("processes/<int:pk>/delete/", views.admin_process_delete, name="admin_process_delete"),
]
