from django.urls import path
from . import views

app_name = "integrations"

urlpatterns = [
    path("sova/ingest/", views.sova_ingest, name="sova_ingest"),
]