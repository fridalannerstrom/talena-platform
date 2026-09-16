from django.urls import path

from . import views


app_name = "candidate_results"

urlpatterns = [
    path("<str:token>/", views.candidate_result, name="result"),
]
