from django.apps import AppConfig


class ProcessesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.processes"

    def ready(self):
        # Focused model modules keep the already large processes/models.py file
        # from growing further. Importing them here registers the models with
        # the processes app.
        from . import interview_question_models  # noqa: F401
        from . import process_settings_models  # noqa: F401

        # Register automatic invitation request/model hooks.
        from . import automatic_invitations  # noqa: F401

        # Personality questions use a dedicated endpoint policy so trait mode can
        # support eight selections while competency mode keeps its six-item cap.
        # Install before the URLconf binds callbacks from views.py.
        from .personality_question_selection_policy import (
            install_personality_question_selection_policy,
        )

        install_personality_question_selection_policy()
