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
