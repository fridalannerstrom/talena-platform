from django import forms
from .models import TestProcess, Candidate

class TestProcessCreateForm(forms.ModelForm):
    # vi lägger till ett “template choice”-fält som vi fyller i viewen
    name = forms.CharField(required=True)
    sova_template = forms.ChoiceField(widget=forms.RadioSelect, required=True)

    
    job_title = forms.CharField(required=False)
    job_location = forms.CharField(required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = TestProcess
        fields = ["name", "sova_template", "job_title", "job_location", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class CandidateCreateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()