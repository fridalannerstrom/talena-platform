from django.urls import path
from .views import sova_project_detail, sova_projects
from . import views

urlpatterns = [
    path("sova/projects/", views.sova_projects, name="sova_projects"),
    path("sova/projects/<str:account_code>/<str:project_code>/", views.sova_project_detail, name="sova_project_detail"),
    path("meta/", views.projectmeta_list, name="projectmeta_list"),
]