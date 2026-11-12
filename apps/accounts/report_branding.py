"""Shared, tenant-aware branding primitives for current and future PDF exports.

Branding is intentionally distinct from Talena's own application chrome.
No remote URLs are accepted. Image URLs point to access-controlled Django routes,
never raw Azure Blob URLs.
"""
from __future__ import annotations

import io
import re

from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_PRIMARY = "#FF6F61"
MAX_LOGO_BYTES = 5 * 1024 * 1024
MAX_COVER_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
ALLOWED_IMAGE_FORMATS = frozenset({"PNG", "JPEG", "WEBP"})
HEX_PATTERN = re.compile(r"^#[A-Fa-f0-9]{6}$")


def normalize_hex(value):
    value = (value or "").strip()
    if not HEX_PATTERN.fullmatch(value):
        raise ValueError("Choose a colour in #RRGGBB format.")
    return value.upper()


def _rgb(color):
    color = normalize_hex(color)
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _hex(rgb):
    return "#" + "".join(f"{round(min(255, max(0, channel))):02X}" for channel in rgb)


def _blend(color, destination, amount):
    source = _rgb(color)
    return _hex([source[i] * (1 - amount) + destination[i] * amount for i in range(3)])


def _luminance(color):
    def linear(channel):
        channel /= 255.0
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    r, g, b = (_rgb(color))
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def _contrast(color_a, color_b):
    high, low = sorted((_luminance(color_a), _luminance(color_b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def brand_palette(primary):
    """Make readable text and stable report/chart accent shades from one HEX."""
    primary = normalize_hex(primary)
    ink = "#141414" if _contrast(primary, "#141414") >= _contrast(primary, "#FFFFFF") else "#FFFFFF"
    return {
        "primary": primary,
        "on_primary": ink,
        "light": _blend(primary, (255, 255, 255), 0.91),
        "medium": _blend(primary, (255, 255, 255), 0.62),
        "dark": _blend(primary, (0, 0, 0), 0.27),
        "chart_colors": [
            primary,
            _blend(primary, (255, 255, 255), 0.38),
            _blend(primary, (0, 0, 0), 0.24),
            _blend(primary, (255, 255, 255), 0.67),
        ],
    }


def get_report_branding(company):
    """Stable config contract; use it from team, individual and merged PDF flows.

    The caller must already have access to the company/report. This helper
    never performs access checks itself, and never returns raw storage URLs.
    """
    from apps.accounts.models import CompanyBranding

    config = CompanyBranding.objects.filter(company_id=company.pk).first()
    primary = (config.primary_color if config else DEFAULT_PRIMARY)
    if not HEX_PATTERN.fullmatch(primary or ""):
        primary = DEFAULT_PRIMARY
    prefix = {"company_pk": company.pk}
    return {
        "company_name": company.name,
        "is_custom": config is not None,
        "palette": brand_palette(primary),
        "cover_focus_y": min(100, max(0, config.cover_focus_y)) if config else 50,
        "logo_url": reverse("accounts:company_branding_asset", kwargs={**prefix, "kind": "logo"}) if config and config.logo else None,
        "cover_url": reverse("accounts:company_branding_asset", kwargs={**prefix, "kind": "cover"}) if config and config.cover_image else None,
    }


def normalize_brand_image(uploaded, kind):
    """Re-encode a validated raster image, stripping EXIF and other metadata.

    Never retain arbitrary uploaded file contents, SVG, GIF, EXIF, or filenames.
    """
    if kind not in {"logo", "cover"}:
        raise ValueError("Unsupported image type.")
    max_bytes = MAX_LOGO_BYTES if kind == "logo" else MAX_COVER_BYTES
    if not uploaded or uploaded.size > max_bytes:
        raise ValueError("The image exceeds the upload size limit.")
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("Use a PNG, JPEG or WebP image.")
            if getattr(source, "n_frames", 1) > 1:
                raise ValueError("Animated images are not supported.")
            width, height = source.size
            if not width or not height or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions are too large.")
            source = ImageOps.exif_transpose(source)
            source.thumbnail((1800, 1800) if kind == "logo" else (2600, 1800), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            if kind == "logo":
                if source.mode != "RGBA":
                    source = source.convert("RGBA")
                stripped = Image.new("RGBA", source.size)
                stripped.paste(source)
                stripped.save(output, format="PNG", optimize=True)
                suffix = "png"
            else:
                stripped = Image.new("RGB", source.size, "white")
                if source.mode in {"RGBA", "LA"}:
                    source = source.convert("RGBA")
                    stripped.paste(source, mask=source.getchannel("A"))
                else:
                    stripped.paste(source.convert("RGB"))
                stripped.save(output, format="JPEG", quality=88, optimize=True)
                suffix = "jpg"
        return ContentFile(output.getvalue(), name=f"{kind}.{suffix}")
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise ValueError("The image could not be processed. Please upload a valid PNG, JPEG or WebP.") from exc
    finally:
        uploaded.seek(0)
