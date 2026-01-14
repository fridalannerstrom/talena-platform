from django import forms
from .models import TestProcess

class TestProcessCreateForm(forms.ModelForm):
    # vi lägger till ett “template choice”-fält som vi fyller i viewen
    name = forms.CharField(required=True)
    status = forms.ChoiceField(choices=[("draft","Draft"),("active","Active")])
    sova_template = forms.ChoiceField(widget=forms.RadioSelect, required=True)

    
    job_title = forms.CharField(required=False)
    job_location = forms.CharField(required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = TestProcess
        fields = ["name", "sova_template", "job_title", "job_location", "notes", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
