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

## Confirmed Sova payload structure (2026-11-03)

A full, completed synthetic/internal assessment was verified against the
Sova recruiter Integrity Guard UI and the corresponding actual score callback.
Sova sends **more than the headline**. Relevant data shape (illustrative,
never an actual candidate payload):

```json
{
  "integrity_guard": {
    "status": 2,
    "status_description": "Concerns Detected",
    "integrity_findings": [
      {"diagnostic": 1, "diagnostic_status": 1, "activities": [
        {"activity": "TQ Personality", "status": 1}
      ]},
      {"diagnostic": 4, "diagnostic_status": 2, "activities": [
        {"activity": "TQ Personality", "status": 2},
        {"activity": "TQ Verbal Reasoning", "status": 1}
      ]}
    ]
  }
}
```

Numbered diagnostic mappings, compared with the Sova recruiter UI:
- 1: IP address
- 2: Devices used
- 3: Browser patrolling
- 4: Question engagement

Each `diagnostic_status` and each nested `activities[].status` is 1 (clear),
2 (concern), or 3 (monitoring error). The nested status belongs to the
monitoring **check within that assessment**, not test completion. Unknown
numeric IDs are displayed neutrally, never assigned an invented meaning.

The four descriptions and all status labels are static Swedish/English
copy. The UI expands each check to show individual monitored assessments,
defaulting the concern section open.

### Existing candidates / rollout

Prior to this update the webhook handler stored the original callback in
`TestInvitation.sova_payload`, but the original parser discarded the nested
findings. `TestInvitation.integrity_guard_display` now prefers already
normalised findings in `integrity_guard`, and otherwise reparses the retained
`sova_payload`. Previously completed candidates can therefore show details
immediately after the code deploy **without retesting or a data migration**.
Future callbacks persist the full normalised check/assessment data.

Migration 0066 was required by the original introduction of the field and
is **not introduced or changed** by this follow-up. The existing Sova
authentication/webhook routing remains unchanged; the separate legacy
callback security issue #309/PR #346 must still be handled independently.

Protect raw assessment payloads: never put candidate IDs, names, scores,
links or tokens in GitHub issues, logs, regression fixtures, or public chats.
Always use synthetic examples. Do not expose Integrity Guard in the
candidate's personal report or Talena AI requests.

## Automated regression tests

`python manage.py test apps.core.test_sova_integrity_guard`

Tests use synthetic, de-identified examples derived from the now-confirmed
Sova payload schema. Keep regression fixtures free of real candidate data.
