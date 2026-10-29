"""Internal-only form for tenant-scoped report branding."""
from django import forms
from django.core.files.uploadedfile import UploadedFile
from PIL import Image

from .models import CompanyBranding
from .report_branding import (
    ALLOWED_IMAGE_FORMATS,
    MAX_COVER_BYTES,
    MAX_IMAGE_PIXELS,
    MAX_LOGO_BYTES,
    normalize_hex,
)


class CompanyBrandingForm(forms.ModelForm):
    remove_logo = forms.BooleanField(required=False)
    remove_cover_image = forms.BooleanField(required=False)

    class Meta:
        model = CompanyBranding
        fields = ["logo", "cover_image", "primary_color", "cover_focus_y"]
        widgets = {
            "logo": forms.FileInput(attrs={"class": "form-control", "accept": ".png,.jpg,.jpeg,.webp"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".png,.jpg,.jpeg,.webp"}),
            "primary_color": forms.TextInput(attrs={"class": "form-control", "maxlength": "7", "placeholder": "#FF6F61"}),
            "cover_focus_y": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100", "step": "1"}),
        }

    def clean_primary_color(self):
        try:
            return normalize_hex(self.cleaned_data["primary_color"])
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_cover_focus_y(self):
        value = self.cleaned_data["cover_focus_y"]
        if value is None or not 0 <= value <= 100:
            raise forms.ValidationError("Choose a number between 0 and 100.")
        return value

    def _validate_image(self, value, kind):
        if not isinstance(value, UploadedFile):
            return value
        max_bytes = MAX_LOGO_BYTES if kind == "logo" else MAX_COVER_BYTES
        if value.size > max_bytes:
            raise forms.ValidationError(
                "Logo images must be under 5 MB." if kind == "logo" else "Cover images must be under 10 MB."
            )
        try:
            value.seek(0)
            with Image.open(value) as img:
                if img.format not in ALLOWED_IMAGE_FORMATS or getattr(img, "n_frames", 1) > 1:
                    raise forms.ValidationError("Use a non-animated PNG, JPEG or WebP.")
                if img.width * img.height > MAX_IMAGE_PIXELS:
                    raise forms.ValidationError("Image is too large (maximum 12 megapixels).")
        except (OSError, ValueError) as exc:
            raise forms.ValidationError("Invalid or unsupported image.") from exc
        finally:
            value.seek(0)
        return value

    def clean_logo(self):
        return self._validate_image(self.cleaned_data.get("logo"), "logo")

    def clean_cover_image(self):
        return self._validate_image(self.cleaned_data.get("cover_image"), "cover")
