from django.urls import path
from . import team_report_views, views
from apps.activity.report_export_receipts import confirm_team_report_export

app_name = "teams"

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("create/", views.team_create, name="team_create"),
    path("<int:pk>/", team_report_views.team_detail, name="team_detail"),
    path("<int:pk>/reports/export-receipt/", confirm_team_report_export,
         name="team_report_export_receipt"),
    path("<int:pk>/insights/<str:insight_type>/generate/", team_report_views.generate_team_insight_view, name="team_insight_generate"),
    path("<int:pk>/delete/", views.team_delete, name="team_delete"),
    path("<int:pk>/members/", views.team_members_edit, name="team_members_edit"),
    path("<int:pk>/edit/", views.team_edit, name="team_edit"),
]
