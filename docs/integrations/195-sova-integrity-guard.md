# Sova Integrity Guard in Talena

Tickets: #195 (ingestion), #88 (candidate list), #89 (candidate detail), #90 (explanatory copy).

## Scope and safety

- Sova Integrity Guard is **not** AI. Talena displays deterministic, static
  status text. It does not send flags, diagnostics, descriptions or monitoring
  evidence to OpenAI and does not include them in AI insight/manager reports.
- The candidate-facing result portal is intentionally excluded. This feature
  is shown only in authorised customer/admin candidate and project views.
- Signals indicate a possible need to review. They are **not** a conclusion
  about cheating or candidate suitability.
- No screen recordings, images, raw IP histories or independent monitoring are
  collected by Talena's Integrity Guard integration. We use Sova scores.

## Data flow and fields

1. An authenticated POST to `/integrations/sova/ingest/` is validated
   using the configured `X-Talena-Webhook-Secret` header.
2. `apps/core/integrations/integrity_guard.py` searches for *explicitly named*
   Integrity Guard score objects/keys, including camelCase and snake_case.
   It does **not** mistake a personality competency named `Integrity` for
   this monitoring system.
3. Normalised data is stored on `TestInvitation.integrity_guard` using the
   new `processes.0066_testinvitation_integrity_guard` migration (after
   `0065_candidate_project_removal`).
4. Stored keys:
   - `overall_status` 0 = not monitored, 1 = all clear, 2 = concerns, 3 = error,
     or `null` when Sova omits this value.
   - `overall_description` (optional Sova-supplied text).
   - `diagnostics` (only monitored checks, statuses 1/2/3).
   - `sources` (individual normalised results from the score payload).
5. An update with **no** Guard fields does not clear an existing Guard result.
   Missing data remains unknown, never an all-clear.
6. The visual summary considers **all** returned assessments and diagnostics:
   concern takes priority, then error, then all-clear, then not-monitored.
   Each monitored diagnostic remains separately visible in candidate details.
   If Sova sends multiple assessments independently rather than one combined
   score snapshot, verify vendor semantics before changing merge behaviour.

## UI

- One compact shield next to a candidate's name in current-process lists.
  Green check: no concerns; amber question: review; red exclamation: error;
  neutral grey: explicitly not monitored. No Guard data: no shield.
- Candidate overview shows the shield, a static non-accusatory explanation,
  and any available monitored diagnostic statuses and Sova description.
- Swedish and English strings are included. Neither Sova's data nor these
  strings are sent to the AI pipeline.

## Production rollout / verification

The earlier sandbox PR #395 was never merged. It used hypothetical score
fixtures and an opt-in local ngrok callback. This implementation is rebased
conceptually onto current `main`, intentionally **without** exposing a new
callback endpoint or adding local ngrok configuration.

**Before considering #195 fully verified:**

1. Confirm which of Talena's two Sova webhook paths production actually uses.
   The authenticated ingest path above captures Guard. The legacy
   `/webhooks/sova/` endpoint remains a separate security issue (#309/PR #346).
   **Do not blindly merge PR #346** without confirming the callback header:
   it can reject production callbacks with 401.
2. Deploy this change using the normal GitHub flow, run migration
   `python manage.py migrate`, and verify 0066 was applied.
3. Order a **new synthetic internal** Sova assessment in a production project
   with Integrity Guard enabled. Complete it and check in authorised Django
   Admin that `TestInvitation.integrity_guard` contains status/description/
   per-diagnostic values. No sensitive candidate payloads in logs/issues/chat.
4. Compare the real Sova field names/structure to the aliases in the parser.
   If different, update the parser and add a **redacted synthetic regression
   fixture**. Only then consider the real score mapping confirmed.
5. Check statuses 1/2/3 and 0 when available; no data, omitted diagnostics
   and repeated callbacks. Verify the candidate list and candidate card,
   including both Swedish and English, show the appropriate state.
6. Confirm a Sova result without Guard still processes as before, and test
   score/status delivery and candidate result notification normally.
7. Confirm no monitoring data appears in candidate-facing reports or AI
   requests. This is explicitly outside the AI interpretation pipeline.

## Automated regression tests

`python manage.py test apps.core.test_sova_integrity_guard`

Tests use synthetic Sova data only. Passing them does not prove that the
real vendor's payload schema matches the aliases.
