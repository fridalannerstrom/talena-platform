from django import forms
from django.contrib.auth import get_user_model
from apps.accounts.models import Profile

User = get_user_model()

class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("image",)

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if not img:
            return img

        # max 2MB
        if img.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Max file size is 2MB.")

        # tillåt bara jpg/png/webp (enkel kontroll)
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if hasattr(img, "content_type") and img.content_type not in allowed:
            raise forms.ValidationError("Only JPG, PNG or WEBP files are allowed.")

        return img