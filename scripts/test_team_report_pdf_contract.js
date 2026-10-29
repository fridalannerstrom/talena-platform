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

for (const marker of [
  "data-team-report-summary", "data-team-report-composite", "data-team-report-maximum-numeric",
  "data-team-report-insights", "data-team-report-members", "data-team-report-download",
  "data-team-report-brand-primary", "data-team-report-brand-logo", "data-team-report-brand-cover"
]) assert.ok(tpl.includes(marker), "team template missing: " + marker);

assert.ok(core.includes("pdf.setProperties"), "PDF metadata should be explicitly controlled");
assert.ok(js.includes('const body = newElement("main", "team-report-pdf-body")'), "report sections should be laid out continuously");
assert.ok(js.includes('{ node: body, continuous: true }'), "PDF must capture continuous body once");
assert.ok(!js.includes("...parts.map(node => ({ node }))],"), "no standalone page per small section");

const vm = require("node:vm");
const sandbox = { window: {} };
vm.runInNewContext(core, sandbox, { timeout: 1000 });
const paginate = sandbox.window.TalenaPdfExport.calculatePageSlices;
assert.equal(typeof paginate, "function");

function verifySlices(height, maxPage, boundaries, maxExpectedPages) {
  const slices = paginate(height, maxPage, boundaries);
  assert.ok(slices.length <= maxExpectedPages, "too many near-empty pages");
  assert.equal(slices[0].start, 0);
  assert.equal(slices[slices.length - 1].start + slices[slices.length - 1].height, height);
  for (const [index, slice] of slices.entries()) {
    assert.ok(slice.height > 0 && slice.height <= maxPage);
    if (index > 0) {
      assert.equal(slice.start, slices[index - 1].start + slices[index - 1].height);
    }
  }
  return slices;
}
verifySlices(400, 1000, [], 1);
verifySlices(2750, 1000, [100, 300, 750, 1600, 1800, 2600], 4);
verifySlices(1500, 1000, [70, 150, 300], 2);
verifySlices(4800, 1000, [950, 1910, 3100, 4000], 6);
const natural = verifySlices(2250, 1000, [760, 1780], 3);
assert.equal(natural[0].height, 760, "a near-page-end card boundary should be preferred");

assert.ok(core.includes("pdf.save("), "download must produce a real PDF");
console.log("Team report PDF contract: anonymous whitelist, branding, and export wiring OK");
