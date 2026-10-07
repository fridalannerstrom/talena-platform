from django import forms
from django.core.exceptions import ValidationError
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
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        if self.company is None and self.instance.pk:
            self.company = self.instance.company
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

    def clean_name(self):
        name = self.cleaned_data["name"]
        if self.company is None:
            return name

        duplicate_teams = Team.objects.filter(
            company=self.company,
            name=name,
        )
        if self.instance.pk:
            duplicate_teams = duplicate_teams.exclude(pk=self.instance.pk)

        if duplicate_teams.exists():
            language = translation.get_language() or "en"
            message = (
                "Ett team med det här namnet finns redan i företaget."
                if language.startswith("sv")
                else _("A team with this name already exists in this company.")
            )
            raise ValidationError(message)

        return name
