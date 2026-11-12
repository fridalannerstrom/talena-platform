from django.db import migrations


TARGET_PROMPTS = {
    "post_interview_decision_support": {
        "name": "After interview · Combined interpretation",
        "description": (
            "Controls only the Combined interpretation / Samlad tolkning "
            "section in After interview."
        ),
    },
    "post_interview_supported_indications": {
        "name": "After interview · Role support",
        "description": (
            "Controls the Stöd för rollen / Role support section in "
            "After interview."
        ),
    },
    "post_interview_added_nuance": {
        "name": "After interview · Additional nuance (background)",
        "description": (
            "Background-only post-interview nuance retained for backwards "
            "compatibility. It is not a main section in the candidate UI."
        ),
    },
    "post_interview_contradictions": {
        "name": "After interview · Areas to explore",
        "description": (
            "Controls the Områden att utforska / Areas to explore section "
            "in After interview."
        ),
    },
    "post_interview_remaining_uncertainties": {
        "name": "After interview · Remaining evidence gaps",
        "description": (
            "Controls Kvar att utforska / Remaining evidence gaps in "
            "After interview."
        ),
    },
    "post_interview_suggested_follow_up": {
        "name": "After interview · Next steps",
        "description": (
            "Controls the Nästa steg / Next steps section in After interview."
        ),
    },
}


def refresh_post_interview_prompts(apps, schema_editor):
    AIPromptTemplate = apps.get_model(
        "processes",
        "AIPromptTemplate",
    )

    db_alias = schema_editor.connection.alias

    for key, metadata in TARGET_PROMPTS.items():
        prompts = (
            AIPromptTemplate.objects
            .using(db_alias)
            .filter(key=key)
        )

        # System-created prompt rows contain copies of the previous protected
        # defaults. Remove those so runtime falls back to the new role-context
        # defaults installed in the prompt registry. Administrator-edited
        # prompts are deliberately preserved.
        prompts.filter(updated_by__isnull=True).delete()

        prompts.filter(updated_by__isnull=False).update(
            name=metadata["name"],
            description=metadata["description"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0056_seed_ai_prompt_versions"),
    ]

    operations = [
        migrations.RunPython(
            refresh_post_interview_prompts,
            migrations.RunPython.noop,
        ),
    ]
