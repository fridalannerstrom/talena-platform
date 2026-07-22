from django import forms
from django.contrib.auth import get_user_model
from django.forms.widgets import ClearableFileInput
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Profile


User = get_user_model()


class AccountForm(forms.ModelForm):
    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs
        )

        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                }
            )


class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile

        fields = (
            "image",
        )

        widgets = {
            "image": ClearableFileInput(
                attrs={
                    "class": (
                        "form-control "
                        "form-control-sm"
                    ),
                    "accept": (
                        "image/jpeg,"
                        "image/png,"
                        "image/webp"
                    ),
                }
            ),
        }

    def clean_image(self):
        image = self.cleaned_data.get(
            "image"
        )

        if not image:
            return image

        max_size = 2 * 1024 * 1024

        if image.size > max_size:
            raise forms.ValidationError(
                _("Max file size is 2MB.")
            )

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        if (
            hasattr(image, "content_type")
            and image.content_type
            not in allowed_types
        ):
            raise forms.ValidationError(
                _(
                    "Only JPG, PNG or WEBP "
                    "files are allowed."
                )
            )

        return image