"""Launch safeguard: disable the legacy free-form AI chat endpoints.

Ticket #302. Both the candidate/person chat and the general chat can accept
sensitive free-text prompts. Neither has a product-help-only input boundary.
Return 404 before reading request data, loading candidate context or creating
an OpenAI client.

The URLs remain registered so legacy links fail safely and Django URL
reversals in older templates do not break. A future product-help chatbot must
be implemented separately, with a restrictive scope and privacy tests.
"""

from django.http import HttpResponseNotFound, JsonResponse


def chat_view(request):
    """No free-form AI chat page during launch."""
    return HttpResponseNotFound("Not found.")


def chat_api(request):
    """Block the original non-streaming free-form chat API."""
    return JsonResponse({"error": "Not found."}, status=404)


def chat_stream_api(request):
    """Block candidate and general streaming chat before processing a prompt."""
    return JsonResponse({"error": "Not found."}, status=404)
