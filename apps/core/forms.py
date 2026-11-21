# forms.py (exempel)
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": "input",
        "placeholder": "example-user",
        "autocomplete": "username",
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "input",
        "placeholder": "••••••••••••••",
        "autocomplete": "current-password",
    }))

from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm


class TalenaPasswordResetForm(PasswordResetForm):
    """Use Talena's existing input styling for the secure Django reset flow."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({
            "class": "input",
            "autocomplete": "email",
            "placeholder": "name@example.com",
        })


class TalenaSetPasswordForm(SetPasswordForm):
    """Keep Django's configured password validation and token handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("new_password1", "new_password2"):
            self.fields[field].widget.attrs.update({
                "class": "input",
                "autocomplete": "new-password",
            })
