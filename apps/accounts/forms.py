from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class CreateCustomerUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]  # lägg till company senare

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "customer"
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user