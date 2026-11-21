"""Persist and apply per-user UI language without changing Django's cookie behavior.

Language is a global User preference (not Company or Project language).
Legacy users without a saved preference continue using LocaleMiddleware's
browser/cookie selection. Existing {% url 'set_language' %} forms keep their
original Django path and response while authenticated selections are saved.
"""
from django.conf import settings
from django.utils import translation
from django.views.i18n import set_language as django_set_language
from django.utils.deprecation import MiddlewareMixin

TALENA_UI_LANGUAGES = frozenset(("sv", "en"))


class UserLanguagePreferenceMiddleware(MiddlewareMixin):
    """Run after AuthenticationMiddleware; override LocaleMiddleware if saved."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return
        language = getattr(user, "preferred_language", "")
        if language in TALENA_UI_LANGUAGES:
            translation.activate(language)
            request.LANGUAGE_CODE = language


def talena_set_language(request):
    """Use Django's safe language-switch response and remember logged-in choices."""
    response = django_set_language(request)
    if request.method == "POST" and request.user.is_authenticated:
        language = request.POST.get("language")
        allowed = {code for code, _label in settings.LANGUAGES}
        if language in TALENA_UI_LANGUAGES and language in allowed:
            if request.user.preferred_language != language:
                # Only the logged-in account can be changed by this public form.
                type(request.user).objects.filter(pk=request.user.pk).update(
                    preferred_language=language
                )
                request.user.preferred_language = language
    return response
