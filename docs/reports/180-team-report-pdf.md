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
  A4, raster per logical report section, multi-page slicing, PDF metadata,
  real browser download; no backend report storage.
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
