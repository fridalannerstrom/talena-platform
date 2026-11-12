# Ticket #327: Human edits in the Manager Report

## Editable content

Only narrative AI content in the Manager Report is editable:

- `wellbeing_tips` in the “For the manager” section.
- The six personality report paragraphs: `testbild` and `candidate_describes` for each of the three personality themes.

Scores, percentiles, test scales, static guidance and other assessment facts are not editable through this feature. Server validation accepts only the listed narrative block keys.

## Storage and access

`ManagerReportTextEdit` stores the current human override, keyed by process, candidate, block and language. It stores the latest saved version, the user who last changed it, and timestamps. Candidate and process deletion cascade to both the override and its audit metadata.

The read endpoint uses process view access. Saving and restoring an AI paragraph requires process edit access, so viewers can read but cannot change report text. The endpoint also verifies that the candidate belongs to the requested process, validates the report language and limits text to 30,000 characters. POST requests use Django CSRF protection.

The override remains separate from the generated AI result. Updates to AI content do not change the saved human override. “Restore AI text” removes the override and displays the latest generated text.

## Regeneration behavior

When a user regenerates content that has a manual override, the UI asks before continuing. Regeneration updates the AI source while preserving the saved override in the report. The regenerated AI text is available by choosing “Restore AI text” in that block’s editor. If the AI generation fails, the saved override stays visible.

The Manager Report and its print-to-PDF export use the same displayed DOM. The report stays hidden and its PDF button stays disabled until the authorized edit endpoint has loaded all saved overrides.

## Audit metadata

`ManagerReportTextEditEvent` records the process, candidate ID, actor, block key, language, action, edit version, source AI generation timestamp and event timestamp. Audit events do not store the report text. No customer-facing endpoint exposes these events.
