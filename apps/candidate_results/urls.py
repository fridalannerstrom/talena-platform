from django.urls import path

from . import views


app_name = "candidate_results"

urlpatterns = [
    path("manage/<int:invitation_id>/", views.manage_candidate_result, name="manage"),
    path("preview/<int:snapshot_id>/", views.candidate_result_preview, name="preview"),
    path("<str:token>/", views.candidate_result, name="result"),
]
