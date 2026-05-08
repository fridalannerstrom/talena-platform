from django.urls import path
from . import views

app_name = "emails"

urlpatterns = [
    path(
        "processes/<int:process_id>/email-template/invitation/",
        views.edit_process_invitation_template,
        name="edit_process_invitation_template",
    ),

    path(
        "admin/companies/<int:company_pk>/processes/<int:process_pk>/email-template/invitation/",
        views.admin_edit_company_process_invitation_template,
        name="admin_edit_company_process_invitation_template",
    ),
]