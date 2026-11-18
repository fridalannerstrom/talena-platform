class AuthTraceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Never log complete paths: query strings may contain access tokens.
        return self.get_response(request)

class AIPiiMaskingNoticeMiddleware:
    """Expose a boolean privacy notice only for requests that reached OpenAI.

    Synchronous responses use a response header. NDJSON streams receive one
    harmless event, emitted only after a sanitized outbound request.
    The original prompt and masked identifiers are never exposed.
    """

    HEADER = "X-Talena-AI-PII-Masked"
    EVENT = '{"type":"ai_privacy_masked"}\n'

    def __init__(self, get_response):
        self.get_response = get_response

    @classmethod
    def _stream_events(cls, source, state, actor_id=None):
        from apps.core.ai.privacy_notice import privacy_request_scope
        from apps.core.ai.usage_metrics import ai_usage_actor_scope

        sent = False
        with privacy_request_scope(state), ai_usage_actor_scope(actor_id):
            for chunk in source:
                if state.masked_sent and not sent:
                    sent = True
                    yield cls.EVENT.encode("utf-8") if isinstance(chunk, bytes) else cls.EVENT
                yield chunk
            if state.masked_sent and not sent:
                yield cls.EVENT

    @classmethod
    async def _async_stream_events(cls, source, state, actor_id=None):
        from apps.core.ai.privacy_notice import privacy_request_scope
        from apps.core.ai.usage_metrics import ai_usage_actor_scope

        sent = False
        with privacy_request_scope(state), ai_usage_actor_scope(actor_id):
            async for chunk in source:
                if state.masked_sent and not sent:
                    sent = True
                    yield cls.EVENT.encode("utf-8") if isinstance(chunk, bytes) else cls.EVENT
                yield chunk
            if state.masked_sent and not sent:
                yield cls.EVENT

    @staticmethod
    def _stream_with_actor(source, actor_id):
        from apps.core.ai.usage_metrics import ai_usage_actor_scope
        with ai_usage_actor_scope(actor_id):
            yield from source

    @staticmethod
    async def _async_stream_with_actor(source, actor_id):
        from apps.core.ai.usage_metrics import ai_usage_actor_scope
        with ai_usage_actor_scope(actor_id):
            async for chunk in source:
                yield chunk

    def __call__(self, request):
        from apps.core.ai.privacy_notice import (
            PrivacyRequestState,
            privacy_request_scope,
        )
        from apps.core.ai.usage_metrics import ai_usage_actor_scope, usage_logging_enabled

        # AuthenticationMiddleware runs first. Never obtain attribution from
        # a URL, client payload, cookie string, or a generated AI response.
        user = getattr(request, "user", None)
        actor_id = (
            user.pk if user is not None and user.is_authenticated and user.is_active
            else None
        ) if usage_logging_enabled() else None
        state = PrivacyRequestState()
        with privacy_request_scope(state), ai_usage_actor_scope(actor_id):
            response = self.get_response(request)

        is_ndjson = response.streaming and response.get(
            "Content-Type", ""
        ).startswith("application/x-ndjson")
        # Preserve existing file/other stream behavior when metering is off.
        if response.streaming and (is_ndjson or actor_id is not None):
            original_stream = response.streaming_content
            if response.is_async:
                response.streaming_content = (
                    self._async_stream_events(original_stream, state, actor_id)
                    if is_ndjson
                    else self._async_stream_with_actor(original_stream, actor_id)
                )
            else:
                response.streaming_content = (
                    self._stream_events(original_stream, state, actor_id)
                    if is_ndjson
                    else self._stream_with_actor(original_stream, actor_id)
                )
        elif not response.streaming and state.masked_sent:
            response[self.HEADER] = "1"
        return response
