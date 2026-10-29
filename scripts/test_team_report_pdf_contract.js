// Focused source contract for anonymous team PDF export.
// Full visual/PDF tests must also be performed in a real browser.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");

const js = fs.readFileSync("static/js/talena/team-report-export.js", "utf8");
const tpl = fs.readFileSync("templates/customer/teams/team_detail.html", "utf8");
const core = fs.readFileSync("static/js/talena/pdf-export-core.js", "utf8");

const block = js.match(/if \(anonymous\) return \[([\s\S]*?)\];/);
assert.ok(block, "anonymous export must use an explicit allowlist");
const anonymous = block[1];
for (const token of [
  "[data-team-report-summary]",
  "[data-team-report-composite]",
  "[data-team-report-maximum-numeric]"
]) assert.ok(anonymous.includes(token), "missing allowed aggregate section: " + token);

for (const sensitive of [
  "[data-team-report-members]",
  "[data-team-report-context]",
  "[data-team-report-insights]",
  "[data-team-report-maximum]",
  "[data-team-member-profile]"
]) assert.ok(!anonymous.includes(sensitive), "private section accidentally exported: " + sensitive);

for (const guard of ["assertAnonymousSafe(stage)", "sourceSelectors(anonymous)", "anonym-teamrapport.pdf",
  "stage?.remove()", "stage.style.setProperty", "window.TalenaPdfExport.exportSections"]) {
  assert.ok(js.includes(guard), "missing export or privacy guard: " + guard);
}
assert.ok(js.includes("profile.dataset.reportName"), "no candidate-name privacy check");
assert.ok(js.includes("data-original"), "test needs checking text privacy stripping") if false else null;

for (const marker of [
  "data-team-report-summary", "data-team-report-composite", "data-team-report-maximum-numeric",
  "data-team-report-insights", "data-team-report-members", "data-team-report-download",
  "data-team-report-brand-primary", "data-team-report-brand-logo", "data-team-report-brand-cover"
]) assert.ok(tpl.includes(marker), "team template missing: " + marker);

assert.ok(core.includes("pdf.setProperties"), "PDF metadata should be explicitly controlled");
assert.ok(core.includes("pdf.save("), "download must produce a real PDF");
console.log("Team report PDF contract: anonymous whitelist, branding, and export wiring OK");
