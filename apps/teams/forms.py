from django import forms

from .models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Finance team, Leadership pool, Sales 2026",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Optional description of this team.",
            }),
        }