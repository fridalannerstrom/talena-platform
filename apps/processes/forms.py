from django import forms
from .models import TestProcess, Candidate

class TestProcessCreateForm(forms.ModelForm):
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
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = getattr(self, "instance", None)
        if instance and instance.pk and instance.is_template_locked():
            self.fields["sova_template"].disabled = True
            self.fields["sova_template"].help_text = (
                "Testpaketet kan inte ändras efter att tester har skickats i processen."
            )


class CandidateCreateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
    

class SelfRegisterForm(forms.Form):
    name = forms.CharField(max_length=255)
    email = forms.EmailField()