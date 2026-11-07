"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const tabs = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const copy = fs.readFileSync("static/js/talena/candidate-eyebrows.js", "utf8");
const view = fs.readFileSync("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html", "utf8");
const shell = fs.readFileSync("templates/customer/core/layouts/customer_base.html", "utf8");
const header = fs.readFileSync("templates/customer/processes/_process_header.html", "utf8");

// New candidates always start with evidence. They cannot open an ungenerated
// analysis tab, even via a stale query string.
assert.ok(tabs.includes('const keys = ["evidence", "overview", "interview", "explore", "managerReport"]'));
assert.ok(tabs.includes('if (key !== "evidence" && !hasCompiledPostInterviewResult)'));
assert.ok(tabs.includes('button.setAttribute("aria-disabled", "true")'));
assert.ok(tabs.includes('if (button && !button.disabled) activate(button.dataset.afterInterviewTab)'));
assert.ok(tabs.includes('(hasCompiledPostInterviewResult || key === "evidence")'));
assert.ok(tabs.includes('hasCompiledPostInterviewResult ? "overview" : "evidence"'));
assert.ok(tabs.includes('lastRenderedCompiled === false && hasCompiledPostInterviewResult'));

// The guided flow complements the existing save, compile and report controls.
for (const snippet of [
  "journeyTitle:", "journeySteps:", "evidenceHeading:", "evidenceHeadingReady:",
  'journey.append(journeyHeading, journeySteps)',
  'tabs.append(journey, navSection, tabPanels)',
  'evidenceCard.append(evidenceIntro, notesRoot, postSection)',
  'panels.get("evidence").appendChild(evidenceCard)',
]) {
  assert.ok(tabs.includes(snippet), "Missing guided journey element: " + snippet);
}
assert.ok(copy.includes("testresultat, roll- och processkontext"));
assert.ok(copy.includes("assessment results, role and process context"));
assert.ok(view.includes("data-interview-notes-save"));
assert.ok(view.includes("data-post-interview-generate"));
assert.ok(view.includes('rows="8"'));
assert.ok(shell.includes("after-interview-tabs.js") && shell.includes("guided-v2"));
assert.ok(header.includes("candidate-eyebrows.js") && header.includes("guided-after"));

console.log("After interview guided flow contract passed.");
