from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class InviteUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]  # justera efter dina fält

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("En användare med den e-posten finns redan.")
        return email