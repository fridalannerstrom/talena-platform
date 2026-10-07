from django import forms
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from .models import Team


TEAM_GOAL_CHOICES = [
    ("understand_collaboration", _("Understand how we collaborate"), _("Förstå hur vi samarbetar")),
    ("develop_communication", _("Develop our communication"), _("Utveckla vår kommunikation")),
    ("discover_strengths", _("Discover strengths and development areas"), _("Upptäcka styrkor och utvecklingsområden")),
    ("support_team_development", _("Support the team’s development"), _("Stödja teamets utveckling")),
]


class TeamForm(forms.ModelForm):
    goals = forms.MultipleChoiceField(
        choices=(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label=_("What would you like to explore?"),
    )

    class Meta:
        model = Team
        fields = [
            "name",
            "description",
            "goals",
            "context",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _(
                        "Example: Finance team, Leadership pool, Sales 2026"
                    ),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": _(
                        "Optional description of this team."
                    ),
                }
            ),
            "context": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": _(
                        "Describe the team, its current situation or what you would like Talena to take into account."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = translation.get_language() or "en"
        use_swedish = language.startswith("sv")
        self.fields["goals"].choices = [
            (key, sv_label if use_swedish else en_label)
            for key, en_label, sv_label in TEAM_GOAL_CHOICES
        ]
        # Retain older selections if the preset list is edited or retired.
        existing_goals = (self.instance.goals or []) if self.instance.pk else []
        known = {key for key, _, _ in TEAM_GOAL_CHOICES}
        self.fields["goals"].choices += [
            (goal, goal.replace("_", " ").capitalize())
            for goal in existing_goals
            if goal not in known
        ]
        if self.instance.pk:
            self.initial.setdefault("goals", existing_goals)
