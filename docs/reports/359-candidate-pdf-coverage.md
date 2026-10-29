# Ticket #359: candidate report PDF export coverage

Status: **first tested implementation slice**, on a draft PR. Not yet complete.

## Implementation / shared contract

- `static/js/talena/candidate-report-pdf.js` registers report id, parent panel,
  optional subpanel, Swedish/English label and its availability prerequisite.
- `TalenaCandidateReportPdf.availableReports(workspace)` returns available
  authorized report *descriptors* for future #360 selection.
- `TalenaCandidateReportPdf.exportReport(workspace, id, {returnBlob})` exports
  the same HTML content already present in that candidate's currently loaded,
  access-controlled process view. It has no fetches, AI calls, new endpoints
  or persistent PDF storage.
- Each PDF uses the shared browser `TalenaPdfExport.exportSections`, including
  the optional Blob path for #360. A full-bleed title page uses the customer's
  authorized logo, cover image, primary palette and cropping, otherwise Talena's
  standard. A PNG with alpha is rendered without an opaque CSS backing.
- `apps.processes.views.build_candidate_detail_context` and the historical
  equivalent receive company-scoped branding. No new report endpoint or
  cross-tenant access is introduced.
- Neutral filenames never contain a candidate name or email. Only the current
  process/authorized candidate is used; registered report ids are constants,
  not selectors supplied by the user.

## Coverage matrix

| Candidate screen/subtab | First-slice status | Reason |
|---|---|---|
| Sammanfattning / Overview | Implemented | Existing authorized overview; direct rendered snapshot |
| Personlighet > Resultat | Implemented | Requires personality results |
| Motivation > Resultat | Implemented | Requires motivation results |
| Färdighet > Resultat | Implemented | Requires ability results |
| Rapporter > Teamrapport (individual) | Implemented | Requires `team_style_profile.available` |
| Rapporter > Ledarskapsrapport | Implemented | Requires `leadership_report_content.has_results` |
| Rapporter > Urspårningsrapport | Implemented | Requires `derailment_report_content.has_results` |
| Personlighet/Motivation/Färdighet > Tolkning | **Next slice** | Must require saved completed interpretation, not auto-generate AI |
| Personlighet/Motivation/Färdighet > Frågor | **Next slice** | Must check saved question status, exclude unsaved notes |
| Resultatflikar > Kandidatens reflektioner | **Review** | May contain candidate-provided personal data; needs export policy |
| Inför intervju | **Next slice** | Must confirm saved/ready decision support; no hidden AI draft |
| Efter intervju > Helhetsbild, Intervjusammanfattning, Undersök vidare, Tips för trivsel, Underlag | **Next slice** | Dynamic saved content and generated state need explicit checks |
| Efter intervju > Chefsrapport | Existing PDF under #357 | Avoid replacing a working editor/PDF until shared engine integration is tested |
| Navigation/status/action-only panels | Not applicable | Not independent reports |
| Sova's original external PDF files | Existing Sova link | Do not misrepresent external Sova PDF as a Talena-rendered component |
| Candidate's public static report (#293) | Separate candidate portal | No AI should be added or generated |

## Readiness, privacy and stability

- The UI renders a button only for results that currently exist per report
  readiness flags. An unavailable report cannot be rendered via the public
  `exportReport` method either.
- The exporter snapshots the authorized DOM and *only* snapshots visible
  canvases, replacing them with images. Hidden panels, buttons, forms, input
  fields, unsaved interview notes, AI-loading UI and transient attributes are
  excluded from the PDF.
- Existing server-side process/organization permission checks govern whether
  the user can obtain the candidate sheet; the exporter performs no other
  network requests.
- The branded A4 cover is now always exactly one page. Previous height
  rounding could add a 1-pixel overflow blank page in the common team report.

## Manual release gate

1. Open one authorized synthetic candidate with PQ/MQ/ability results.
2. Exercise each registered button, compare PDF content against the selected
   tab and check that no navigation, input fields or loading placeholders show.
3. Open a synthetic candidate who lacks one of these results, confirm those
   buttons are absent and any direct JS API call refuses the missing type.
4. Test the three standalone reports under Rapporter with graphical SVGs and
   multi-page bodies, Swedish/English text, and company branding.
5. Test historical candidates and cross-company users; ensure neither can
   access reports outside their original authorized context.
6. Test long reports, hidden charts, large logos and cover images, and that
   the existing Chefsrapport and team PDF/ZIP functionality is unchanged.

**Do not close #359 or start merging/report packages (#360) as though all
candidate report types are ready.** This slice is intended to establish a
stable, reusable foundation and get actual PDFs reviewed before covering the
many dynamic AI-backed sections.
