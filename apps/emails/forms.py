from django import forms
from .models import EmailTemplate

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["subject", "body", "language", "is_active"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 10}),
        }