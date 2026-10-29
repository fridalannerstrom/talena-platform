from django.urls import path
from . import views

app_name = "integrations"

urlpatterns = [
    path("sova/ingest/", views.sova_ingest, name="sova_ingest"),
    path("sova/local/<str:token>/", views.sova_local_ingest, name="sova_local_ingest"),
]