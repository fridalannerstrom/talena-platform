from django.urls import path

from . import views
from .pinned_projects import toggle_pinned_project
from .access_control import (
    process_edit_access_required,
    process_view_access_required,
)
from .automatic_invitations import (
    capture_automatic_candidate_invitations,
    capture_process_automatic_invitation_setting,
    process_automatic_invitation_setting,
)
from .interview_question_notes import (
    process_candidate_interview_question_note_update,
    process_candidate_interview_question_notes,
    process_candidate_post_interview_decision_support_regenerate_with_evidence,
    process_candidate_post_interview_decision_support_stream_with_evidence,
)

app_name = "processes"

urlpatterns = [
    path("", views.process_list, name="process_list"),
    path(
        "<int:pk>/edit/",
        capture_process_automatic_invitation_setting(views.process_update),
        name="process_update",
    ),
    path("<int:pk>/delete/", views.process_delete, name="process_delete"),
    path("<int:pk>/pin/", toggle_pinned_project, name="toggle_pinned_project"),
    path(
        "new/",
        capture_process_automatic_invitation_setting(views.process_create_v2),
        name="process_create",
    ),
    path("<int:pk>/", views.process_detail, name="process_detail"),
    path(
        "<int:pk>/add-candidate/",
        capture_automatic_candidate_invitations(views.process_add_candidate),
        name="process_add_candidate",
    ),
    path(
        "<int:pk>/automatic-invitation-setting/",
        process_automatic_invitation_setting,
        name="process_automatic_invitation_setting",
    ),
    path("<int:process_id>/candidate/<int:candidate_id>/", views.process_candidate_detail, name="process_candidate_detail"),

    # Public self-registration route.
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
    path(
        "<int:process_id>/candidates/<int:candidate_id>/summary/stream/",
        views.process_candidate_summary_stream,
        name="process_candidate_summary_stream",
    ),
    path("<int:pk>/role-context/", views.process_role_context, name="process_role_context"),
    path(
        "<int:process_id>/candidates/<int:candidate_id>/summary/regenerate/",
        views.process_candidate_summary_regenerate,
        name="process_candidate_summary_regenerate",
    ),
    path(
        "processes/<int:process_id>/candidates/<int:candidate_id>/purpose-fit/stream/",
        views.process_candidate_purpose_fit_stream,
        name="process_candidate_purpose_fit_stream",
    ),
    path(
        "processes/<int:process_id>/candidates/<int:candidate_id>/purpose-fit/regenerate/",
        views.process_candidate_purpose_fit_regenerate,
        name="process_candidate_purpose_fit_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "response-style-guidance/stream/"
        ),
        views.process_candidate_response_style_guidance_stream,
        name="process_candidate_response_style_guidance_stream",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/cognitive-interpretation/stream/"
        ),
        views.process_candidate_cognitive_interpretation_stream,
        name="process_candidate_cognitive_interpretation_stream",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/cognitive-interpretation/regenerate/"
        ),
        views.process_candidate_cognitive_interpretation_regenerate,
        name="process_candidate_cognitive_interpretation_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/motivation-interpretation/stream/"
        ),
        views.process_candidate_motivation_interpretation_stream,
        name="process_candidate_motivation_interpretation_stream",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/motivation-interpretation/regenerate/"
        ),
        views.process_candidate_motivation_interpretation_regenerate,
        name="process_candidate_motivation_interpretation_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/motivation-questions/stream/"
        ),
        views.process_candidate_motivation_questions_stream,
        name="process_candidate_motivation_questions_stream",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/motivation-questions/regenerate/"
        ),
        views.process_candidate_motivation_questions_regenerate,
        name="process_candidate_motivation_questions_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/personality-questions/stream/"
        ),
        views.process_candidate_personality_questions_stream,
        name="process_candidate_personality_questions_stream",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/personality-questions/regenerate/"
        ),
        views.process_candidate_personality_questions_regenerate,
        name="process_candidate_personality_questions_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/personality-traits/update/"
        ),
        views.process_candidate_personality_traits_update,
        name="process_candidate_personality_traits_update",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/personality-interpretation/stream/"
        ),
        views.process_candidate_personality_interpretation_stream,
        name="process_candidate_personality_interpretation_stream",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/personality-interpretation/regenerate/"
        ),
        views.process_candidate_personality_interpretation_regenerate,
        name="process_candidate_personality_interpretation_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/combined-questions/"
        ),
        views.process_candidate_combined_questions,
        name="process_candidate_combined_questions",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/final-output/"
        ),
        views.process_candidate_final_output,
        name="process_candidate_final_output",
    ),
    path(
        "<int:process_id>/candidate/<int:candidate_id>/"
        "cognitive-questions/stream/",
        views.process_candidate_cognitive_questions_stream,
        name="process_candidate_cognitive_questions_stream",
    ),
    path(
        "<int:process_id>/candidate/<int:candidate_id>/"
        "cognitive-questions/regenerate/",
        views.process_candidate_cognitive_questions_regenerate,
        name="process_candidate_cognitive_questions_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "pre-interview-decision-support/stream/"
        ),
        views.process_candidate_pre_interview_decision_support_stream,
        name="process_candidate_pre_interview_decision_support_stream",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "pre-interview-decision-support/regenerate/"
        ),
        views.process_candidate_pre_interview_decision_support_regenerate,
        name="process_candidate_pre_interview_decision_support_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "interview-notes/update/"
        ),
        views.process_candidate_interview_notes_update,
        name="process_candidate_interview_notes_update",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/interview-question-notes/"
        ),
        process_candidate_interview_question_notes,
        name="process_candidate_interview_question_notes",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/interview-question-notes/update/"
        ),
        process_candidate_interview_question_note_update,
        name="process_candidate_interview_question_note_update",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "post-interview-decision-support/stream/"
        ),
        process_candidate_post_interview_decision_support_stream_with_evidence,
        name="process_candidate_post_interview_decision_support_stream",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "post-interview-decision-support/regenerate/"
        ),
        process_candidate_post_interview_decision_support_regenerate_with_evidence,
        name="process_candidate_post_interview_decision_support_regenerate",
    ),
    path(
        (
            "<int:process_id>/candidate/"
            "<int:candidate_id>/ai-insights/update-plan/"
        ),
        views.process_candidate_global_ai_update_plan,
        name="process_candidate_global_ai_update_plan",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "response-style-guidance/stream/"
        ),
        views.process_candidate_response_style_guidance_stream,
        name="process_candidate_response_style_guidance_stream",
    ),
    path(
        (
            "<int:process_id>/candidates/"
            "<int:candidate_id>/"
            "response-style-guidance/regenerate/"
        ),
        views.process_candidate_response_style_guidance_regenerate,
        name="process_candidate_response_style_guidance_regenerate",
    ),
]


# Candidate-facing process endpoints historically used a company-only helper in
# parts of views.py. Wrap them centrally so direct URLs and AI endpoints always
# respect the same org-unit Viewer/Editor/Own scope as the process list.
_PROCESS_VIEW_ROUTE_NAMES = {
    "process_candidate_detail",
    "process_candidate_combined_questions",
    "process_candidate_final_output",
    "process_candidate_interview_question_notes",
}

_PROCESS_EDIT_ROUTE_NAMES = {
    # Core process write routes. Keep these centrally guarded even though the
    # views also perform local checks, so a future refactor cannot accidentally
    # weaken Viewer/Editor/Own permissions.
    "process_update",
    "process_delete",
    "process_add_candidate",
    "remove_candidate_from_process",
    "process_send_tests",
    "process_archive",
    "process_unarchive",

    # Candidate/AI write routes.
    "process_candidate_summary_stream",
    "process_candidate_summary_regenerate",
    "process_candidate_purpose_fit_stream",
    "process_candidate_purpose_fit_regenerate",
    "process_candidate_response_style_guidance_stream",
    "process_candidate_response_style_guidance_regenerate",
    "process_candidate_cognitive_interpretation_stream",
    "process_candidate_cognitive_interpretation_regenerate",
    "process_candidate_motivation_interpretation_stream",
    "process_candidate_motivation_interpretation_regenerate",
    "process_candidate_motivation_questions_stream",
    "process_candidate_motivation_questions_regenerate",
    "process_candidate_personality_questions_stream",
    "process_candidate_personality_questions_regenerate",
    "process_candidate_personality_traits_update",
    "process_candidate_personality_interpretation_stream",
    "process_candidate_personality_interpretation_regenerate",
    "process_candidate_cognitive_questions_stream",
    "process_candidate_cognitive_questions_regenerate",
    "process_candidate_pre_interview_decision_support_stream",
    "process_candidate_pre_interview_decision_support_regenerate",
    "process_candidate_interview_notes_update",
    "process_candidate_interview_question_note_update",
    "process_candidate_post_interview_decision_support_stream",
    "process_candidate_post_interview_decision_support_regenerate",
    "process_candidate_global_ai_update_plan",
}

for pattern in urlpatterns:
    if pattern.name in _PROCESS_EDIT_ROUTE_NAMES:
        pattern.callback = process_edit_access_required(pattern.callback)
    elif pattern.name in _PROCESS_VIEW_ROUTE_NAMES:
        pattern.callback = process_view_access_required(pattern.callback)
