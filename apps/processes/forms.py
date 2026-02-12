from django import forms
from .models import TestProcess, Candidate

class TestProcessCreateForm(forms.ModelForm):
    name = forms.CharField(required=True)

    sova_template = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=True
    )

    labels_text = forms.CharField(
        required=False,
        help_text="Skriv en eller flera labels, separera med kommatecken. Ex: Admin, Interim, Prioritet",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ex: Admin, Interim, Prioritet",
        })
    )

    class Meta:
        model = TestProcess
        fields = ["name", "sova_template", "labels_text"]

    def clean_labels_text(self):
        raw = (self.cleaned_data.get("labels_text") or "").strip()
        if not raw:
            return []
        
        # Split by comma, normalize + dedupe
        parts = [p.strip() for p in raw.split(",")]
        parts = [p for p in parts if p]
        normalized = []
        seen = set()
        for p in parts:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                normalized.append(p[:50])  # max length safety
        return normalized
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Bootstrap styling ---
        self.fields["name"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "T.ex. Säljare – Stockholm",
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
    first_name = forms.CharField(
        max_length=150,
        label="Förnamn",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"})
    )
    last_name = forms.CharField(
        max_length=150,
        label="Efternamn",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"})
    )
    email = forms.EmailField(
        label="E-post",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"})
    )