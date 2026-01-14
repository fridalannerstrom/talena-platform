from django import forms
from .models import TestProcess

class TestProcessCreateForm(forms.ModelForm):
    # vi lägger till ett “template choice”-fält som vi fyller i viewen
    sova_template = forms.ChoiceField(label="Mall (SOVA Project)", choices=[])

    class Meta:
        model = TestProcess
        fields = ["name", "sova_template", "job_title", "job_location", "notes", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }