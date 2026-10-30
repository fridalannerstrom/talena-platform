# Ticket #355: Helhetsbild with structured evidence and independent generation

## Scope

The existing **Efter intervju → Helhetsbild** legacy Markdown is retained. The
new `ai_post_interview_decision_support.overall_picture_structured` property
uses a versioned JSON structure inside the existing saved result (no database
migration). Other After interview tabs, Chefsrapport and the static
candidate-facing report remain separate.

### Four editable admin prompts

In the existing Talena admin prompt registry, available in Swedish and English:

| Section | Key |
| --- | --- |
| Färdighet | `post_interview_overall_skills` |
| Motivation | `post_interview_overall_motivation` |
| Personlighet | `post_interview_overall_personality` |
| Sammanfattande helhetsbild | `post_interview_overall_synthesis` |

Review these defaults against the business owners' complete approved
`post_interview_overall_picture` override. The legacy override is kept for
old reports and is **not silently erased or rewritten**. Prompt registry
history/restore/preview continues to work via standard admin mechanisms.

### Generation contract

- Skills: only actual available Sova cognitive results, ordered numerical,
  logical, verbal, with approved practitioner test interpretations.
- Motivation: precisely the three highest-scored actual Sova motivation factors,
  using available human-readable localized labels and definitions.
- Personality: a controlled selection call returns descriptive work themes
  from role context and approved candidate-specific personality summaries;
  each theme's call gets only its selected trait summaries.
- Interview sources: general notes and saved question notes scoped to the
  relevant assessment source, with each **exact question text** attached
  to its saved answer/note. Do not present interviewer notes as quotes.
- Each successful item stores its separate `testbild` / `intervjun` fields,
  status and evidence/prompt fingerprint. The final synthesis uses the prior
  structured sections, not an unbounded raw assessment payload.
- Model calls use JSON response mode, server-side validation, and
  `redact_candidate_name` before the privacy-protected OpenAI client.
- Cached candidate-level job guard prevents repeated concurrent attempts
  in a shared-cache deployment. Distributed deployments should configure a
  shared cache if cross-worker deduplication is required.
- Partial failures keep prior content, and source changes flag existing
  structured sections stale. The final synthesis becomes stale whenever a
  source section changes.
- Existing full `Sammanställ underlag` action requests `?structured=1` and
  still orchestrates other content blocks. Single-section regeneration
  requests `?block=overall_picture&structured=1&section=<key>`.
- After a complete structured version is ready, a human-readable legacy
  `content_blocks.overall_picture` Markdown mirror is saved for older clients.
  Until then the prior legacy report remains readable in the customer UI.

### Manual QA before merging

1. On a test candidate with Numerisk, Logisk, Verbal, PQ, MQ, role context
   and completed interview answers, run **Sammanställ underlag**.
2. Confirm 3 skill cards, top 3 real motivation factors, grounded personality
   theme cards (normally 5–7 only if evidence warrants it), and final synthesis.
3. Compare Swedish narrative depth, factual distinctions, and nuanced Testbild
   and Intervjun prose against the current approved 1,500–2,000-word example.
4. Repeat with English language, one or two missing tests and missing
   topic-specific interview evidence. No invented anecdotes or raw IDs.
5. Regenerate one category; verify that other sections persist, and final
   synthesis becomes stale until regenerated.
6. Trigger a failed/partial generation; confirm older valid texts remain
   readable, with explicit error states, no duplicate submissions.
7. Refresh and switch tabs; check the data persists and no unintended
   regeneration starts on view.
8. Verify same-company permissions; no names, email or unnecessary
   cross-category test data sent to OpenAI in mocked payload logs.
9. Run `node scripts/test_structured_overall_picture_contract.js`,
   `python manage.py test apps.core.test_structured_overall_picture`, and CI.

This PR deliberately stays in draft until synthetic browser QA and qualitative
content review are complete. No candidate-facing AI feature is added.
