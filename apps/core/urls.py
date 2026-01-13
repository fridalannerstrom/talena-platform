from django.urls import path
from .views import customer_dashboard, admin_dashboard
from . import views

urlpatterns = [
    path("dashboard/", customer_dashboard, name="customer_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("sova/projects/", views.sova_projects, name="sova_projects"),
    path("sova/projects/<str:account_code>/<str:project_code>/", views.sova_project_detail, name="sova_project_detail"),
]