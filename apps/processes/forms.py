from django import forms
from .models import TestProcess, Candidate

class TestProcessCreateForm(forms.ModelForm):
    name = forms.CharField(required=True)
    sova_template = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=True
    )

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

        # --- Bootstrap styling ---
        self.fields["name"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "T.ex. Säljare – Stockholm",
        })

        self.fields["job_title"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "T.ex. Säljare",
        })

        self.fields["job_location"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "T.ex. Stockholm",
        })

        self.fields["notes"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Valfritt: kravprofil, interna anteckningar…",
            "rows": 5,
        })

        # RadioSelect får inte form-control, men vi kan lägga klass på ul:
        self.fields["sova_template"].widget.attrs.update({
            "class": "template-picker-list"
        })

        # --- Din befintliga lock-logik ---
        instance = getattr(self, "instance", None)
        if instance and instance.pk and instance.is_template_locked():
            self.fields["sova_template"].disabled = True
            self.fields["sova_template"].help_text = (
                "Testpaketet kan inte ändras efter att tester har skickats i processen."
            )

class CandidateCreateForm(forms.Form):
    first_name = forms.CharField(
        label="Förnamn",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Förnamn",
            "autocomplete": "given-name"
        })
    )
    last_name = forms.CharField(
        label="Efternamn",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Efternamn",
            "autocomplete": "family-name"
        })
    )
    email = forms.EmailField(
        label="E-post",
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "namn@företag.se",
            "autocomplete": "email"
        })
    )

class SelfRegisterForm(forms.Form):
    name = forms.CharField(max_length=255)
    email = forms.EmailField()