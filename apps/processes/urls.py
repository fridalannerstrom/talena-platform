from django.urls import path
from . import views
from django.urls import path, include

app_name = "processes"

urlpatterns = [
    path("processes/", views.process_list, name="process_list"),
    path("processes/new/", views.process_create, name="process_create"),
    path("processes/<int:pk>/edit/", views.process_update, name="process_update"),
    path("processes/<int:pk>/delete/", views.process_delete, name="process_delete"),
    path("processes/<int:pk>/", views.process_detail, name="process_detail"),
    path("processes/<int:pk>/add-candidate/", views.process_add_candidate, name="process_add_candidate"),
    path("processes/<int:pk>/invite/<int:candidate_id>/", views.invite_candidate, name="invite_candidate"),
    path("processes/<int:process_id>/candidate/<int:candidate_id>/", views.process_candidate_detail, name="process_candidate_detail"),
    path("<int:pk>/smoke-invite/<int:candidate_id>/", views.sova_order_assessment_smoke_test, name="sova_order_assessment_smoke_test"),
    path("r/<uuid:token>/", views.self_register, name="self_register"),
]