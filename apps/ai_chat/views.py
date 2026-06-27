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

from apps.accounts.utils.org_access import (
    get_company_for_user,
    user_can_view_process,
)

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
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
        payload = json.loads(
            request.body.decode("utf-8") or "{}"
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
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
        TestProcess.objects.select_related("company"),
        id=process_id,
    )

    company = get_company_for_user(request.user)

    if (
        not company
        or process.company_id != company.id
        or not user_can_view_process(
            request.user,
            company,
            process,
        )
    ):
        return JsonResponse(
            {
                "error": (
                    "You do not have access to this process."
                )
            },
            status=403,
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
    You are Talena, an assessment interpretation assistant.

    Your role is to help the user understand the candidate, not to merely
    repeat raw assessment data.

    Use only the candidate assessment data and process context provided.

    Interpretation rules:
    - Interpret patterns across relevant assessment results.
    - Explain what the results may mean in practical working life.
    - Translate scores into clear, natural and useful language.
    - Focus on likely motivators, preferences, strengths, risks and areas
    worth exploring.
    - Connect the interpretation to the user's question.
    - Do not present a long inventory of scores.
    - Do not begin answers with labels such as "Evidence:",
    "Interpretation:" or "Conclusion:" unless the user explicitly asks
    for a formal breakdown.
    - Mention individual scores only when they help explain the answer.
    - For personality results, always use STEN rounded as the primary score.
    - Do not use percentiles to interpret personality results.
    - Treat STEN 1–3 as lower, 4–7 as typical or moderate, and 8–10 as higher.
    - For motivation results, use the scale provided in the candidate data.
    - For cognitive ability results, percentiles may be used when relevant.
    - Do not invent scores, behaviours or conclusions.
    - Clearly distinguish likely tendencies from confirmed behaviour.
    - Use cautious language such as "may", "suggests" and "could indicate".
    - Do not make diagnoses or final hiring decisions.
    - If the data does not support the question, say so clearly.

    Conversation style:
    - Sound like a knowledgeable assessment consultant having a conversation.
    - Answer directly and naturally.
    - Keep most answers to 2–5 short sentences.
    - Use short bullet points only when they improve clarity.
    - Do not repeat the user's question.
    - Do not summarise the entire profile unless explicitly asked.
    - Avoid mechanical score-by-score reporting.
    - Prioritise interpretation over data repetition.
    """.strip()

    user_prompt = f"""
    Candidate data:

    {candidate_context_json}

    User question:

    {message}

    Give a brief, natural interpretation that directly answers the question.
    Use STEN rounded for personality interpretation and avoid listing every
    score unless necessary.
    """.strip()

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return JsonResponse(
            {
                "error": (
                    "OPENAI_API_KEY is not configured."
                )
            },
            status=500,
        )

    client = OpenAI(api_key=api_key)

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

        except Exception as error:
            print(
                "CANDIDATE CHAT STREAM ERROR:",
                repr(error),
                flush=True,
            )

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