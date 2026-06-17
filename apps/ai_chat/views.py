import json
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.ai.chat import ask_ai
from apps.core.ai.chat_stream import stream_ai


import os


from django.shortcuts import get_object_or_404
from openai import OpenAI

from apps.processes.models import TestProcess
from apps.ai_chat.services.candidate_chat_context import (
    build_candidate_chat_context,
    serialize_candidate_chat_context,
)




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

@login_required
@require_POST
def chat_stream_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON payload."},
            status=400,
        )

    message = (payload.get("message") or "").strip()
    process_id = payload.get("process_id")
    candidate_id = payload.get("candidate_id")

    if not message:
        return JsonResponse(
            {"error": "A message is required."},
            status=400,
        )

    if not process_id or not candidate_id:
        return JsonResponse(
            {
                "error": (
                    "process_id and candidate_id are required."
                )
            },
            status=400,
        )

    process = get_object_or_404(
        TestProcess,
        id=process_id,
        company=request.user.company,
    )

    try:
        chat_context = build_candidate_chat_context(
            process=process,
            candidate_id=candidate_id,
        )
    except (
        HistoricalProcessCandidate.DoesNotExist,
        TestInvitation.DoesNotExist,
    ):
        return JsonResponse(
            {
                "error": (
                    "The candidate could not be found "
                    "in this process."
                )
            },
            status=404,
        )

    candidate_context_json = (
        serialize_candidate_chat_context(
            chat_context
        )
    )

    system_prompt = """
You are Talena's assessment interpretation assistant.

Answer questions using only the candidate assessment data and process
context provided below.

Rules:
- Do not invent assessment scores, behaviours or conclusions.
- Clearly distinguish evidence from interpretation.
- Use cautious language such as "may", "suggests" and "could indicate".
- Do not make diagnoses or claims about mental health.
- Do not make the final hiring decision.
- When context is missing, provide general assessment insights only.
- For historical candidates, use imported assessment data exactly as
  you would use live assessment data.
- If the available data cannot support the question, say so clearly.
- Keep answers practical, structured and relevant to recruitment,
  development, onboarding or team use.
""".strip()

    user_prompt = f"""
Candidate data:

{candidate_context_json}

User question:

{message}
""".strip()

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    def stream_response():
        try:
            stream = client.responses.create(
                model=os.environ.get(
                    "OPENAI_CHAT_MODEL",
                    "gpt-5-mini",
                ),
                instructions=system_prompt,
                input=user_prompt,
                stream=True,
            )

            for event in stream:
                if (
                    event.type
                    == "response.output_text.delta"
                ):
                    yield event.delta

        except Exception:
            yield (
                "\n\nThe AI response could not be "
                "generated right now."
            )

    response = StreamingHttpResponse(
        stream_response(),
        content_type="text/plain; charset=utf-8",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response