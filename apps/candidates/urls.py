from django.urls import path

from . import views

app_name = "candidates"

urlpatterns = [
    path("", views.candidate_list, name="candidate_list"),
]