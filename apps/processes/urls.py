from django.urls import path
from . import views

app_name = "processes"

urlpatterns = [
    path("processes/", views.process_list, name="process_list"),
    path("new/", views.process_create, name="process_create"),
    path("processes/<int:pk>/edit/", views.process_update, name="process_update"),
    path("processes/<int:pk>/delete/", views.process_delete, name="process_delete"),
]