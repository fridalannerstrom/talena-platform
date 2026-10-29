// #181 / #182: both download paths must produce the same branded PDF.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");

const profile = fs.readFileSync("static/js/talena/team-profile-export.js", "utf8");
const core = fs.readFileSync("static/js/talena/pdf-export-core.js", "utf8");
const css = fs.readFileSync("static/css/talena/pages/team-profile-export.css", "utf8");
const sharedCss = fs.readFileSync("static/css/talena/pages/team-report-export.css", "utf8");
const template = fs.readFileSync("templates/customer/teams/team_detail.html", "utf8");

for (const field of [
  "data-team-report-brand-primary", "data-team-report-brand-light",
  "data-team-report-brand-dark", "data-team-report-brand-cover",
  "data-team-report-brand-logo", "data-team-report-brand-focus"
]) assert.ok(template.includes(field), "missing customer-scoped company branding: " + field);
for (const field of [
  "page.dataset.teamReportBrandPrimary",
  "page.dataset.teamReportBrandLight",
  "page.dataset.teamReportBrandDark",
  "page.dataset.teamReportBrandLogo",
  "page.dataset.teamReportBrandCover",
  "page.dataset.teamReportBrandFocus",
  "profile.dataset.reportName",
  "page.dataset.teamReportName",
  "talena-team-pdf-cover", "talena-team-pdf-cover-brand",
  "talena-team-pdf-cover-brand-fallback"
]) assert.ok(profile.includes(field), "missing branded team-profile cover field: " + field);

assert.ok(profile.includes('saveBlob(await createPdf(profile), filename(profile))'),
  "single profile download must use the branded PDF builder");
assert.ok(profile.includes('const blob = await createPdf(available[i]);'),
  "every ZIP item must use the same branded PDF builder");
assert.ok(profile.includes('zip.file(filename(available[i]), blob);'),
  "ZIP must contain a separate PDF per member");
assert.ok(profile.includes('await ensureLibraries(true);'),
  "ZIP must still load JSZip and PDF libraries");
assert.ok(profile.includes('const previouslyOpen = profile.open;'),
  "profile open state must be restored");
assert.ok(profile.includes('profile.open = previouslyOpen;'),
  "profile open state restoration is required");
assert.ok(profile.includes("if (isAnonymous())"),
  "private individual profile export must not run when anonymised");
assert.ok(profile.includes("{ node: cover, cover: true }"),
  "brand cover must be a separate full-bleed A4 page");
assert.ok(profile.includes("{ node: body, continuous: true }"),
  "individual profile contents should be compact and continuous");
assert.ok(profile.includes("returnBlob: true"),
  "individual ZIP entries must not trigger a separate browser download");
assert.ok(core.includes('if (options.returnBlob)'),
  "shared PDF engine needs a Blob-return mode");
assert.ok(core.includes('new Blob([pdf.output("arraybuffer")]'),
  "PDF needs real downloadable binary data");
assert.ok(css.includes(".team-profile-pdf-body"),
  "profile export layout must support the new cover and body");
assert.ok(sharedCss.includes(".talena-team-pdf-cover-brand-fallback"),
  "the white backing is allowed only for text fallback, not PNG logos");
assert.ok(sharedCss.includes("background: transparent;"),
  "uploaded transparent PNG logos must show through the cover");

console.log("Team profile branding and ZIP PDF contract: OK");
