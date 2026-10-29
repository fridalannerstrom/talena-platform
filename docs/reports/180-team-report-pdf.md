# Ticket #180: common team report PDF export

Status: implementation for local review; not merged to main.

## Scope and report boundaries

- The **Download team report** button in the shared Team report exports an A4 PDF
  with a customer-branded title page, summary statistics, team style composite
  chart, ranked averages, saved team AI insight text, maximum-score analysis,
  most/least style table, contextual content, and the authorized member list.
- The individual Team style profiles are deliberately **not** duplicated here.
  Ticket #181 exports each person's individual Team profile as its own PDF/ZIP.
- All data is taken from the existing authorized, rendered team view.
  PDF export never submits reports to Sova/OpenAI and never generates AI.
  Incomplete/nonexistent team scores disable the common export button.

## Anonymized export

The team page's existing anonymity toggle controls export mode too. When enabled:
- The PDF title and filename are generic. Metadata title/author/subject contain
  no team/person names, emails or IDs.
- Only these **three explicitly allowed aggregate numeric sections** are captured:
  summary strip, composite team styles chart/rankings, and maximum-score rankings.
- The team name, context, saved AI narrative, most/least member breakdown,
  member list and all individual member profiles are excluded entirely.
  This fail-closed policy is intentional: AI and user-authored free text can
  contain real names, emails and identifiers.
- A runtime check compares anonymous PDF text to visible candidate names/emails;
  suspicious matches block export. The client also removes source `data-*`,
  `title` and accessibility text attributes from captured fragments.
- The customer-specific report cover/logo is retained; avoid uploading sensitive
  candidate images into a company-level branding configuration.

## Branding

- The shared `apps.accounts.report_branding.get_report_branding(company)` config
  provides the selected primary palette and access-controlled image URLs.
- The PDF cover uses company branding in normal mode. Report headings/accent
  bars use the derived palette; the team-style chart retains its distinct
  categorical colours for legibility.
- The PDF engine is the new `static/js/talena/pdf-export-core.js`:
  A4, a single continuously flowing report body after the cover, multi-page
  slicing near natural card boundaries, PDF metadata, real browser download;
  no backend report storage. Short sections no longer create separate A4 pages.
- PNG logos render directly on the cover image with no imposed white backing.
  The admin preview does the same. Actual image alpha is preserved when the
  logo is uploaded; a PNG that already contains opaque white pixels does not
  become transparent automatically (upload a logo with alpha in that case).
- `#359`, `#360` and the existing `#181` should migrate to this core
  incrementally before their own final tickets can be closed.

## Manual testing before merge

1. Configure customer logo, cover and primary colour under the admin Branding tab.
2. Create/view a synthetic team with complete score data and saved insights.
3. Download non-anonymous PDF. Check pages, charts, bars, context, saved insights,
   member table, Swedish/English glyphs, image crop and company branding.
4. Enable anonymity and download again. Confirm the PDF **does not** include
   candidate names/emails, context, AI narrative, member tables or candidate IDs.
   Search PDF metadata and binary/text extraction for known synthetic identifiers.
5. With an incomplete/no-data team, verify export is unavailable.
6. Verify members outside the team/tenant can't visit the team report or fetch
   another customer's logo/cover directly.
7. Test long AI insights/large teams for clipping, page numbers and browser memory.
8. Retest #181's existing individual PDF/ZIP exports and the anonymity warning.

Known limit: the PDF body uses images of the rendered UI, so text in the
body is not selectable/searchable. More semantically rich PDF construction is
tracked with common report exports (#359/#360); do not treat this version as
the final shared report PDF platform.

## Layout regression: sample 7-page export

The sample PDF supplied during October 2026 UI testing was seven pages, with
most body pages nearly empty because each HTML report section started a new
A4 page. The revised browser export captures the combined report body **once**
while keeping the cover as its own A4 page. Smart slicing places a page break
near a card boundary when it uses at least 72% of the page height. If no suitable
boundary exists, it fills the page rather than generating a largely empty page.

Before closing ticket #180, verify the sample team's new PDF uses fewer pages,
there are no missing sections or split headings/charts, and compare anonymous
and full exports separately. A long team report will still use several pages.

## Individual team profile branding (#181 / #182)

The existing **Ladda ner teamprofil** button inside each member's tab and
**Ladda ner alla teamprofiler** ZIP action now both use the same
`createPdf(profile)` implementation. Every PDF has the selected company's
cover image, transparent PNG logo, primary palette, team name and person's
name. A dedicated branded cover is followed by the existing candidate team
style content, continuously paginated near team-profile card boundaries.

The shared `TalenaPdfExport.exportSections(..., {returnBlob: true})` provides
a PDF Blob without triggering a browser download. An individual button saves
this Blob directly; the bulk action adds **one PDF per available member** into
the ZIP as before. No server-stored PDF or external PDF service was added.

- The existing anonymity toggle still **blocks identifiable individual exports**
  (both single and ZIP), since this report contains individual results.
- Existing incomplete-profile confirmation/skip behavior, unique filenames
  and candidate tab open/close state are preserved.
- PNG alpha requires a genuinely transparent source file. Only the CSS white
  backing was removed, not white pixels inside an opaque bitmap.
- Test a single profile, a multi-person ZIP, ZIP member PDF cover/pages,
  incomplete members, language, and both PNG/cover image combinations locally
  before approval.

## Release gate and next PDF tickets

- Shared branding base #182 was merged independently as PR #397.
- #180 is still awaiting **visual** acceptance of its anonymous-mode PDF.
  The regression `scripts/test_team_report_anonymous_runtime.js` executes
  the export's real allowlist, privacy guard, and anonymous-cover builder
  against synthetic candidate identities and confirms that generic metadata
  and filenames are chosen for anonymous mode.
  This functional test is deliberately not a browser PDF-rendering test.
- Next: #359 establishes export coverage for each authorized report tab and
  a reusable report registry; #360 implements report-package selection,
  ordering, PDF merge and separate ZIP from the same registered PDF components.
- Do not mark #182 complete until report-wide integration is in place.
