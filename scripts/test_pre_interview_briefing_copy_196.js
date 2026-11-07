/* #196 cleanup: approved headings are localized UI copy, not a new synthesis. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/js/talena/pre-interview-briefing.js", "utf8");
const originalLabels = [
  "Kandidatspecifik briefing",
  "Kandidatbild inför intervjun",
  "Hur du kan anpassa ton, direkthet, tempo och uppföljning",
];
for (const label of originalLabels) {
  assert.ok(!source.includes(label), "Obsolete #196 copy remains: " + label);
}
assert.ok(source.includes('summarySection.querySelector(".purpose-fit-section-title")'),
  "The existing saved summary section must still be reused");
assert.ok(source.includes('"[data-pre-interview-overall-synthesis]"'),
  "The existing candidate-specific synthesis must not be replaced");
assert.ok(source.includes("data.discussion_guidance?.feedback_approach"),
  "Candidate-grounded conversation tips must remain");
assert.ok(source.includes("data.cautious_interpretations"),
  "Candidate-specific validation hypotheses must remain");
assert.ok(source.includes("const data = await readSavedBriefing(root);"),
  "The existing saved briefing must still be used");

const doc = {
  documentElement: {lang: "sv"},
  addEventListener() {},
};
const context = {
  window: {},
  document: doc,
  WeakSet,
  MutationObserver: class {observe() {}},
};
vm.runInNewContext(
  source.replace("  const safeArray =", "  window.__copy196 = copy;\n  const safeArray ="),
  context,
);
const sv = context.window.__copy196();
assert.equal(sv.briefingKicker, "Anpassad förberedelse");
assert.equal(sv.summaryTitle, "Sammanfattning inför intervjun");
assert.equal(
  sv.approachIntro,
  "Tips på hur du kan anpassa kommunikationen inför samtalet"
);
assert.equal(sv.approachSectionTitle, "Kommunikationsstrategi");

doc.documentElement.lang = "en";
const en = context.window.__copy196();
assert.equal(en.briefingKicker, "Tailored preparation");
assert.equal(en.summaryTitle, "Interview preparation summary");
assert.equal(en.approachIntro, "Tips on how to adapt your communication before the conversation.");
assert.equal(en.approachSectionTitle, "Communication strategy");
console.log("#196: pre-interview copy and saved-candidate-briefing contract passed.");
