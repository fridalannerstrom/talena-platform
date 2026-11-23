/* Contract test: human review before *both* Chefsrapport PDF export routes. */
"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const read = path => fs.readFileSync(path, "utf8");

const dialog = read("static/js/talena/manager-report-review.js");
const styles = read("static/css/talena/pages/manager-report-review.css");
const inline = read("static/js/talena/after-interview-tabs.js");
const registry = read("static/js/talena/candidate-report-export.js");
const customerBase = read("templates/customer/core/layouts/customer_base.html");
const processBase = read("templates/customer/processes/process_base.html");
const adminMirror = read("templates/admin/accounts/partials/_candidate_customer_presentation_js.html");

for (const expected of [
  "Har du granskat AI-insikterna?",
  "Have you reviewed the AI insights?",
  "Jag har granskat, ladda ner",
  "I've reviewed it, download PDF",
  "Granska rapporten",
  "Review report",
  "intervjuunderlaget",
  "interview evidence",
  "dialog.showModal()",
  'closeWith("approved")',
  'closeWith("review")',
  'dialog.returnValue = "review"',
  'resolve(accepted)',
  'returnToReport(report)',
]) {
  assert.ok(dialog.includes(expected), "Missing human-review behavior/text: " + expected);
}
assert.ok(!dialog.includes("localStorage"), "Do not persist a review approval.");
assert.ok(!dialog.includes("sessionStorage"), "Do not reuse prior review approvals.");
assert.ok(!dialog.includes("fetch("), "Review modal must not send candidate data anywhere.");
assert.ok(!dialog.includes("window.confirm("), "Use Talena's accessible modal.");
assert.ok(styles.includes(".talena-manager-ai-review-dialog::backdrop"));
assert.ok(styles.includes(":focus-visible"));
assert.ok(styles.includes("@media (max-width: 480px)"));

for (const source of [customerBase, processBase, adminMirror]) {
  const review = source.indexOf("js/talena/manager-report-review.js");
  const after = source.indexOf("js/talena/after-interview-tabs.js");
  assert.ok(review >= 0 && after > review,
    "Load the shared review handler before the inline manager report PDF action.");
}
assert.ok(customerBase.includes("css/talena/pages/manager-report-review.css"));

const inlineClick = inline.indexOf('pdfButton.addEventListener("click", async () => {');
assert.ok(inlineClick > 0, "Inline manager report action must await human review.");
const inlineGuard = inline.indexOf("TalenaManagerReportReview.confirm(managerReportCard)", inlineClick);
const inlinePrepare = inline.indexOf("TalenaManagerReportPdf.prepare(outputRoot)", inlineClick);
assert.ok(inlineGuard > inlineClick && inlinePrepare > inlineGuard,
  "Human review must complete BEFORE metadata preparation or PDF creation.");
assert.ok(inline.includes("if (!approved || pdfButton.disabled || !managerReportCard.isConnected) return;"));

const exportStart = registry.indexOf("async function exportReport(id, options = {})");
const exportGuard = registry.indexOf("TalenaManagerReportReview.confirm(originalReport)", exportStart);
const exportPrepare = registry.indexOf("TalenaManagerReportPdf.prepare(workspace)", exportStart);
assert.ok(exportStart >= 0 && exportGuard > exportStart && exportPrepare > exportGuard,
  "Registry downloads must require review before creating manager PDF metadata.");
assert.ok(registry.includes("if (!approved) return null;"));
assert.ok(registry.includes("if (generated != null) message.textContent = copy.success;"),
  "Cancellation must not display a false PDF downloaded success message.");
assert.ok(registry.includes("if (!originalReport?.isConnected || getSource(item) !== originalReport)"),
  "Must not export a different candidate after the confirmation dialog closes.");

console.log("Chefsrapport AI review checkpoint contracts passed.");
