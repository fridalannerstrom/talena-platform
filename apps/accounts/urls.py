from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Customer management (admin)
    path("customers/", views.admin_customers_list, name="admin_customers_list"),
    path("customers/new/", views.admin_customers_create, name="admin_customers_create"),

    # Customer detail (admin)
    path("users/<int:pk>/", views.admin_user_detail, name="admin_user_detail"),

    # ✅ Admin: Process detail (admin)
    path("processes/<int:pk>/", views.admin_process_detail, name="admin_process_detail"),

    path(
    "processes/<int:process_pk>/candidates/<int:candidate_pk>/",
    views.admin_candidate_detail,
    name="admin_candidate_detail",
),

    # Invite acceptance (public)
    path("invite/accept/<uidb64>/<token>/", views.accept_invite, name="accept_invite"),
]