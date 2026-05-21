from django import forms
from .models import TestProcess, Candidate
from .models import ProcessRoleContext

class TestProcessCreateForm(forms.ModelForm):
    name = forms.CharField(required=True)

    sova_template = forms.ChoiceField(
        widget=forms.RadioSelect,
        required=True
    )

    labels_text = forms.CharField(
        required=False,
        help_text="Enter one or more tags that describe the testing process. Separate the tags with commas.",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "E.g. Admin, Interim, Priority",
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
            "placeholder": "E.g. Salesperson, Stockholm",
        })

        # RadioSelect får inte form-control, men vi kan lägga klass på ul:
        self.fields["sova_template"].widget.attrs.update({
            "class": "template-picker-list"
        })

        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            existing = instance.labels.values_list("name", flat=True)
            self.fields["labels_text"].initial = ", ".join(existing)

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

class TestProcessWizardCreateForm(forms.Form):
    purpose = forms.CharField(
        max_length=80,
        widget=forms.HiddenInput()
    )

    selected_tests = forms.MultipleChoiceField(
        choices=[
            ("personality", "Personality"),
            ("motivation", "Motivation"),
            ("verbal", "Verbal"),
            ("logical", "Logical"),
            ("numerical", "Numerical"),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Leadership potential"
        })
    )

    labels_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Admin, Interim, Priority"
        }),
        help_text="Enter one or more tags that describe the testing process. Separate the tags with commas."
    )


class ProcessRoleContextForm(forms.ModelForm):
    class Meta:
        model = ProcessRoleContext
        fields = [
            "role_title",
            "job_advertisement",
            "requirements_profile",
            "competency_profile",
            "must_haves",
            "nice_to_haves",
            "priorities",
            "interview_notes",
        ]

        widgets = {
            "role_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Add a short title..."
            }),
            "job_advertisement": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Add context..."
            }),
            "requirements_profile": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add expectations, criteria or requirements..."
            }),
            "competency_profile": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add important behaviours or competencies..."
            }),
            "must_haves": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add must-haves..."
            }),
            "nice_to_haves": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add nice-to-haves..."
            }),
            "priorities": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add priorities..."
            }),
            "interview_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add notes..."
            }),
        }

    def __init__(self, *args, context_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        config = context_config or {}

        field_config = {
            "role_title": {
                "label": "title_label",
                "help": "title_help",
            },
            "job_advertisement": {
                "label": "job_advertisement_label",
                "help": "job_advertisement_help",
            },
            "requirements_profile": {
                "label": "requirements_profile_label",
                "help": "requirements_profile_help",
            },
            "competency_profile": {
                "label": "competency_profile_label",
                "help": "competency_profile_help",
            },
            "must_haves": {
                "label": "must_haves_label",
                "help": "must_haves_help",
            },
            "nice_to_haves": {
                "label": "nice_to_haves_label",
                "help": "nice_to_haves_help",
            },
            "priorities": {
                "label": "priorities_label",
                "help": "priorities_help",
            },
            "interview_notes": {
                "label": "interview_notes_label",
                "help": "interview_notes_help",
            },
        }

        for field_name, keys in field_config.items():
            if field_name in self.fields:
                label = config.get(keys["label"])
                help_text = config.get(keys["help"])

                if label:
                    self.fields[field_name].label = label

                if help_text:
                    self.fields[field_name].help_text = help_text