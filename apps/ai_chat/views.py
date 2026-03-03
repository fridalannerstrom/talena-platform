import json
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.ai.chat import ask_ai
from apps.core.ai.chat_stream import stream_ai




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


@require_POST
@login_required
def chat_stream_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    # MVP: hårdkoda scope, eller byt till "both" senare
    scope = payload.get("scope") or "base"

    def generator():
        try:
            for chunk in stream_ai(message, scope=scope):
                yield chunk
        except Exception as e:
            yield f"\n\n[Error: {str(e)}]"

    resp = StreamingHttpResponse(generator(), content_type="text/plain; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # viktigt om du kör bakom proxy senare
    return resp