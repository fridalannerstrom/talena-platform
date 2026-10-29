# Ticket #195: Sova Integrity Guard score push

This change stores parsed Integrity Guard signals on `TestInvitation.integrity_guard`.
It does not enable monitoring in Sova, expose scores to customers, or pass them
to OpenAI. **The exact live sandbox JSON schema has not yet been observed.**

## Current mapping

- Search nested webhook data for `integrity_guard`, `integrityGuard`,
  `integrity_guard_results`, `integrity_guard_result`, or
  `integrity_guard_data` objects; also handle flattened
  `integrity_guard_status`/`integrityGuardStatus` and related fields.
- `overall_status`: integer 0-3 (including 0, Not monitored), or null when
  only diagnostics are supplied.
- `overall_description`: supplied textual explanation or null.
- `diagnostics`: map of observed diagnostic names to integer 1-3.
  Missing/unmonitored diagnostics are **not** invented or set to 0.
- `sources`: all matching entries with structural paths so per-assessment
  results are not silently collapsed. The top-level fields are drawn from
  the first entry containing an overall status.
- A callback without Integrity Guard fields leaves previously saved
  `integrity_guard` unchanged. Missing Guard data does not block the usual
  score, candidate-status, report or invitation processing.
- Do not infer cheating, and do not forward these flags automatically to AI.

## Sandbox verification required before closing #195

1. Confirm with Sova which callback URL the sandbox uses. The authenticated
   `/integrations/sova/ingest/` expects the configured test/shared secret
   via `X-Talena-Webhook-Secret`. The legacy `/webhooks/sova/` route
   has a separate security rollout; **do not point Sova at it until its
   authentication is verified** (see #309 / PR #346).
2. Ensure Integrity Guard is enabled in the intended Sova sandbox project.
   Run a **synthetic test candidate** all the way through completion.
3. In Django Admin, inspect the latest `TestInvitation.sova_payload` and
   `project_results` for Guard field **names and nesting**. Do not put
   entire candidate payloads, credentials, invitation links or raw IPs into
   GitHub issues, CI logs or chat. Record only the relevant field schema and
   synthetic/mock values in a fixture.
4. Compare these actual field names with
   `apps/core/integrations/integrity_guard.py`. Extend aliases and tests
   if Sova uses a different structure. Verify Django Admin
   `TestInvitation.integrity_guard` has overall status, any supplied
   description and each **actually monitored** diagnostic.
5. Repeat with a test where Integrity Guard is switched off. Verify absence
   of data does not cause errors. Re-send callbacks with missing diagnostic
   fields to verify safe handling.
6. Run migrations and tests before deployment:
   `python manage.py migrate`
   `python manage.py test apps.core.test_sova_integrity_guard`

Acceptance remains **partially unverified** until a real Sova sandbox
assessment and webhook have passed end to end.

### Reference
Sova Help Centre: https://sovaassessment.zendesk.com/hc/en-gb/articles/30062979480338-How-Integrity-Guard-works

## Direct Sova sandbox → local ngrok (without an Azure Function)

The original Sova Integration API v4 schema permits `status_callback_url` and
`results_callback_url` in an `order-assessment` request. **Sova uses these
only when no global callback is configured.** Therefore this is a testable
route, **not a guarantee** that Sova will use the supplied addresses.

To enable **only on a local machine**, keep the sandbox API configured and
set the following in a local (gitignored) `.env`:

```dotenv
ENVIRONMENT=local
DJANGO_DEBUG=True
SOVA_ENV_BASE=https://api-test.sovaonline.com
SOVA_LOCAL_CALLBACK_BASE_URL=https://YOUR-CURRENT-NGROK-DOMAIN.ngrok-free.dev
SOVA_LOCAL_CALLBACK_TOKEN=GENERATE_A_FRESH_RANDOM_TOKEN_AT_LEAST_32_CHARACTERS
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,YOUR-CURRENT-NGROK-DOMAIN.ngrok-free.dev
DJANGO_CSRF_TRUSTED_ORIGINS=https://YOUR-CURRENT-NGROK-DOMAIN.ngrok-free.dev
```

Generate the token locally with:
`python -c "import secrets; print(secrets.token_urlsafe(32))"`

**Never put the token, full signed callback URL or raw Sova payload in
GitHub, screenshots or chat.** The token is embedded in the callback URL and
can be captured in ngrok's local request inspector and the development HTTP
request logs. Keep both tools local/private, test with only internal synthetic
candidate data, then stop ngrok and rotate/remove the token.

Restart Django after setting the variables, run
`python manage.py migrate`, and verify:
`python manage.py test apps.core.test_sova_integrity_guard`.

Create a **new candidate invitation** inside an **existing sandbox Sova
project**, ensuring `SOVA_ENV_BASE` targets sandbox. The order payload will
include both callback URLs pointing to the same token-protected local path.
Existing invitations are not modified, and retries that reuse an existing
Sova order do not change callback destinations.

Keep ngrok running, complete a synthetic assessment, and check
`http://127.0.0.1:4040` for a POST at
`/integrations/sova/local/.../` (mask the token in any screenshots).

- **POST 200:** Check the corresponding `TestInvitation` in local Django
  Admin for `sova_activities`, `project_results` and `integrity_guard`.
- **POST 404:** Check that the local token and URL settings are loaded,
  and ensure the request hit the correct local-only route.
- **POST 401:** Indicates the ordinary header-protected `/ingest/` route,
  not the local token route, or invalid normal webhook credentials.
- **No POST at all:** Most importantly, Sova may still have a globally
  configured webhook destination that overrides both per-order URL fields.
  In that case a full supplier-generated callback cannot be rerouted from
  Talena's side alone. Synthetic local webhook tests still work, but actual
  sandbox end-to-end testing would need callback configuration access.

This local route does not exist on the ordinary production path. It returns
404 unless `DEBUG=True`, `ENVIRONMENT=local`, both local callback settings
are valid, and `SOVA_ENV_BASE` points at the Sova sandbox.

Do not leave a Django debug server exposed through a public tunnel after
testing. Never use production credentials or actual candidate data in the
local tunnel.
