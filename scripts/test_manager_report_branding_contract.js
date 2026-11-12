/* #182: keep manager PDF export wired to the same company branding as team PDFs. */
const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (p) => fs.readFileSync(p, "utf8");
const manager = read("static/js/talena/after-interview-tabs.js");
const core = read("static/js/talena/pdf-export-core.js");
const root = read("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html");
const base = read("templates/customer/core/layouts/customer_base.html");
const views = read("apps/processes/views.py");
const admin = read("apps/accounts/views.py");
const coverStyle = read("static/css/talena/pages/team-report-export.css");

for (const key of [
  "primary", "light", "dark", "logo", "cover", "focus", "company"
]) {
  assert.ok(root.includes("data-manager-report-brand-" + key + "="), "missing brand " + key);
}
assert.ok(views.includes('"report_branding": get_report_branding(process.company)'),
  "candidate view and refresh must derive tenant branding from process company");
assert.ok(admin.includes('"report_branding": get_report_branding(process.company)'),
  "admin candidate view must derive tenant branding from process company");
assert.ok(base.includes("js/talena/pdf-export-core.js"),
  "candidate pages must load the shared PDF renderer");
assert.ok(base.includes("css/talena/pages/team-report-export.css"),
  "candidate pages must load shared branded cover styling");
assert.ok(coverStyle.includes(".talena-team-pdf-cover"),
  "manager PDF cover must reuse the team report's cover CSS");
for (const marker of [
  "buildManagerReportCover", "managerReportBrandLogo",
  "managerReportBrandCover", "managerReportBrandFocus",
  "managerReportBrandPrimary", "managerReportBrandDark",
  "talena-team-pdf-cover-brand-fallback",
  "window.TalenaPdfExport.exportSections",
  "{ node: cover, cover: true }", "{ node: element, continuous: true }",
  "renderElementAsPdf(printableReport, filename, outputRoot)",
  "printableReport.querySelectorAll", "guide.open = true"
]) assert.ok(manager.includes(marker), "missing branded manager PDF behavior: " + marker);
assert.ok(core.includes(".after-interview-manager-report__personality-theme"),
  "shared PDF renderer must break long manager reports near content blocks");
assert.ok(!manager.includes("window.print()"),
  "manager report must download an actual PDF, not trigger print dialog");
assert.ok(manager.includes("pdfButton.disabled = true"),
  "retain PDF progress lock");
assert.ok(manager.includes("exportShell.remove()"),
  "temporary PDF content must always be removed");

console.log("Manager report branding contract OK");
