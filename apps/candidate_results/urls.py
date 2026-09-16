from django.urls import path

from . import views


app_name = "candidate_results"

urlpatterns = [
    path("preview/<int:snapshot_id>/", views.candidate_result_preview, name="preview"),
    path("<str:token>/", views.candidate_result, name="result"),
]
