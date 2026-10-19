import json
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.ai.chat import ask_ai

from apps.core.ai.language import (
    get_ai_system_language_instruction,
    get_request_ai_language,
)

from apps.core.ai.prompt_templates import (
    get_ai_prompt_instructions,
)

import os


from django.shortcuts import get_object_or_404
from openai import OpenAI

from apps.processes.models import TestProcess, Candidate
from apps.core.ai.candidate_name_privacy import redact_candidate_name
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
        answer = ask_ai(
            message,
            scope="base",
            language_code=get_request_ai_language(
                request
            ),
        )
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

    message = (
        payload.get("message")
        or ""
    ).strip()

    process_id = payload.get("process_id")
    candidate_id = payload.get("candidate_id")

    language_code = get_request_ai_language(
        request
    )

    if not message:
        return JsonResponse(
            {
                "error": (
                    "A message is required."
                )
            },
            status=400,
        )

    if not process_id or not candidate_id:
        return JsonResponse(
            {
                "error": (
                    "process_id and candidate_id "
                    "are required."
                )
            },
            status=400,
        )

    process = get_object_or_404(
        TestProcess.objects.select_related(
            "company"
        ),
        id=process_id,
    )

    company = get_company_for_user(
        request.user
    )

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
                    "You do not have access "
                    "to this process."
                )
            },
            status=403,
        )

    try:
        chat_context = (
            build_candidate_chat_context(
                process=process,
                candidate_id=candidate_id,
            )
        )

    except (
        HistoricalProcessCandidate.DoesNotExist,
        TestInvitation.DoesNotExist,
    ):
        return JsonResponse(
            {
                "error": (
                    "The candidate could not "
                    "be found in this process."
                )
            },
            status=404,
        )

    # ---------------------------------------------------------
    # Candidate and process data
    # ---------------------------------------------------------

    candidate = get_object_or_404(Candidate, pk=candidate_id)
    candidate_context_json = (
        serialize_candidate_chat_context(
            chat_context
        )
    )

    # ---------------------------------------------------------
    # Administrator-controlled AI guidance
    # ---------------------------------------------------------

    admin_instructions = (
        get_ai_prompt_instructions(
            key="candidate_chat",
            language=language_code,
        )
    )

    # ---------------------------------------------------------
    # Talena technical system instructions
    # ---------------------------------------------------------

    system_prompt = (
        "You are an AI component inside Talena. "
        "Follow the administrator-provided AI guidance for "
        "all non-technical candidate assessment analysis, "
        "interpretation, reasoning and communication decisions. "
        "Use the supplied candidate and process data as input. "
        "Do not alter or invent technical assessment data. "
        f"{get_ai_system_language_instruction(
            language_code,
            purpose=process.purpose,
        )}"
    )

    # ---------------------------------------------------------
    # Complete user prompt
    # ---------------------------------------------------------

    user_prompt = f"""
TALENA CANDIDATE DATA

{candidate_context_json}


ADMINISTRATOR AI GUIDANCE

The following guidance is controlled by Talena administrators.

It controls all non-technical decisions about:

- assessment interpretation
- score interpretation
- evidence boundaries
- assumptions
- use of process context
- reasoning
- caution
- conclusions
- answer length
- level of detail
- conversational style
- tone
- communication

{admin_instructions}


USER QUESTION

{message}


TALENA TECHNICAL RESPONSE CONTRACT

Answer the user's question using plain text suitable for Talena's
streaming candidate-chat interface.

Return only the answer text.

Do not return JSON or NDJSON.

Do not use code fences.
""".strip()

    # ---------------------------------------------------------
    # OpenAI
    # ---------------------------------------------------------

    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return JsonResponse(
            {
                "error": (
                    "OPENAI_API_KEY is "
                    "not configured."
                )
            },
            status=500,
        )

    client = OpenAI(
        api_key=api_key
    )

    # ---------------------------------------------------------
    # Streaming response
    # ---------------------------------------------------------

    def stream_response():
        try:
            stream = client.responses.create(
                model=os.environ.get(
                    "OPENAI_CHAT_MODEL",
                    "gpt-5-mini",
                ),
                instructions=redact_candidate_name(system_prompt, candidate),
                input=redact_candidate_name(user_prompt, candidate),
                stream=True,
            )

            for event in stream:
                if (
                    event.type
                    == "response.output_text.delta"
                ):
                    yield event.delta

        except Exception as error:
            # Provider exception text may echo request content. Log the type only.
            print("CANDIDATE CHAT STREAM ERROR:", type(error).__name__, flush=True)

            yield (
                "\n\nThe AI response could not be "
                "generated right now."
            )

    response = StreamingHttpResponse(
        stream_response(),
        content_type=(
            "text/plain; charset=utf-8"
        ),
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response