from django.apps import AppConfig


class ProcessesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.processes"

    def ready(self):
        # InterviewQuestionNote lives in a focused module to keep the already
        # large processes/models.py file from growing further. Importing the
        # module here registers the model with the processes app.
        from . import interview_question_models  # noqa: F401
