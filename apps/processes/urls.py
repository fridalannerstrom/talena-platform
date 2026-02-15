from django.urls import path
from . import views
from django.urls import path, include

app_name = "processes"

urlpatterns = [
    path("", views.process_list, name="process_list"),
    path("new/", views.process_create, name="process_create"),
    path("<int:pk>/edit/", views.process_update, name="process_update"),
    path("<int:pk>/delete/", views.process_delete, name="process_delete"),
    path("<int:pk>/", views.process_detail, name="process_detail"),
    path("<int:pk>/add-candidate/", views.process_add_candidate, name="process_add_candidate"),
    path("<int:pk>/invite/<int:candidate_id>/", views.invite_candidate, name="invite_candidate"),
    path("<int:process_id>/candidate/<int:candidate_id>/", views.process_candidate_detail, name="process_candidate_detail"),
    path("<int:pk>/smoke-invite/<int:candidate_id>/", views.sova_order_assessment_smoke_test, name="sova_order_assessment_smoke_test"),

    # ✅ public route
    path("r/<uuid:token>/", views.self_register, name="self_register"),
    path(
        "<int:process_id>/candidate/<int:candidate_id>/remove/",
        views.remove_candidate_from_process,
        name="remove_candidate_from_process",
    ),
    path("<int:pk>/send-tests/", views.process_send_tests, name="process_send_tests"),
    path("<int:pk>/invitation-statuses/", views.process_invitation_statuses, name="process_invitation_statuses"),
    path("<int:pk>/archive/", views.process_archive, name="process_archive"),
path("<int:pk>/unarchive/", views.process_unarchive, name="process_unarchive"),
]