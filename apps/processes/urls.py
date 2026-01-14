from django.urls import path
from . import views

urlpatterns = [
    path("processes/", views.process_list, name="process_list"),
    path("new/", views.process_create, name="process_create"),
    path("<int:pk>/edit/", views.process_update, name="process_update"),
    path("<int:pk>/delete/", views.process_delete, name="process_delete"),
]