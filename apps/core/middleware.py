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
    def _stream_events(cls, source, state):
        from apps.core.ai.privacy_notice import privacy_request_scope

        sent = False
        with privacy_request_scope(state):
            for chunk in source:
                if state.masked_sent and not sent:
                    sent = True
                    yield cls.EVENT.encode("utf-8") if isinstance(chunk, bytes) else cls.EVENT
                yield chunk
            if state.masked_sent and not sent:
                yield cls.EVENT

    @classmethod
    async def _async_stream_events(cls, source, state):
        from apps.core.ai.privacy_notice import privacy_request_scope

        sent = False
        with privacy_request_scope(state):
            async for chunk in source:
                if state.masked_sent and not sent:
                    sent = True
                    yield cls.EVENT.encode("utf-8") if isinstance(chunk, bytes) else cls.EVENT
                yield chunk
            if state.masked_sent and not sent:
                yield cls.EVENT

    def __call__(self, request):
        from apps.core.ai.privacy_notice import (
            PrivacyRequestState,
            privacy_request_scope,
        )

        state = PrivacyRequestState()
        with privacy_request_scope(state):
            response = self.get_response(request)

        if response.streaming and response.get("Content-Type", "").startswith(
            "application/x-ndjson"
        ):
            original_stream = response.streaming_content
            if response.is_async:
                response.streaming_content = self._async_stream_events(
                    original_stream, state
                )
            else:
                response.streaming_content = self._stream_events(
                    original_stream, state
                )
        elif not response.streaming and state.masked_sent:
            response[self.HEADER] = "1"
        return response
