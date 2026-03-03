import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.ai.chat import ask_ai


@login_required
def chat_view(request):
    return render(request, "customer/chat/chat.html")


@require_POST
@login_required
def chat_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    try:
        answer = ask_ai(message, scope="base")
    except Exception as e:
        # För dev: returnera feltext så du ser vad som händer
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"answer": answer})