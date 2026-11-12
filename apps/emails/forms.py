from django import forms
from .models import EmailTemplate

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["subject", "body", "language", "is_active"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            if name == "language":
                widget.attrs.setdefault("class", "form-select")
            elif name == "is_active":
                widget.attrs.setdefault("class", "form-check-input")
            else:
                widget.attrs.setdefault("class", "form-control")


class CompanyInvitationTemplateForm(forms.ModelForm):
    """Admin-managed company default; language comes from the selected tab."""

    class Meta:
        from .models import CompanyInvitationTemplate
        model = CompanyInvitationTemplate
        fields = ["subject", "body", "is_active"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        from string import Formatter
        from .utils import INVITATION_PLACEHOLDERS

        cleaned = super().clean()
        for field in ("subject", "body"):
            value = cleaned.get(field)
            if not value:
                continue
            try:
                tokens = [
                    field_name
                    for _, field_name, format_spec, conversion in Formatter().parse(value)
                    if field_name is not None
                ]
                if any(name not in INVITATION_PLACEHOLDERS for name in tokens):
                    raise ValueError("Unsupported placeholder")
            except ValueError:
                self.add_error(field, "Use only the listed placeholders, such as {first_name}.")

        body = cleaned.get("body", "")
        if cleaned.get("is_active") and "{assessment_url}" not in body:
            self.add_error("body", "Include {assessment_url} so candidates can open their assessments.")
        return cleaned
