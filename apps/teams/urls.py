from django.urls import path
from . import views

app_name = "teams"

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("create/", views.team_create, name="team_create"),
    path("<int:pk>/", views.team_detail, name="team_detail"),
    path("<int:pk>/members/", views.team_members_edit, name="team_members_edit"),
    path("<int:pk>/edit/", views.team_edit, name="team_edit"),
]