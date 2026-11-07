"use strict";
// After interview: calm, accurate provenance and unified icon-only actions.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const read = file => fs.readFileSync(file, "utf8");
const overall = read("static/js/talena/structured-overall-picture.js");
const badges = read("static/js/talena/candidate-ai-badges.js");
const manager = read("static/js/talena/after-interview-tabs.js");
const actionsCss = read("static/css/talena/pages/candidate-report-export.css");
const shell = read("templates/customer/core/layouts/customer_base.html");
const processHeader = read("templates/customer/processes/_process_header.html");

// Helhetsbild: one label at Färdighet, Motivation, Personlighet and the
// concluding Helhetsbild, only if the section contains generated AI prose.
assert.ok(overall.includes("if (sectionHasAI) {"),
  "The final Helhetsbild synthesis needs the same AI label as other generated sections");
assert.ok(overall.includes('["skills", "Färdighet", "Skills"]'));
assert.ok(overall.includes('["motivation", "Motivation", "Motivation"]'));
assert.ok(overall.includes('["personality", "Personlighet", "Personality"]'));
assert.equal((overall.match(/talena-ai-generated-badge/g) || []).length, 1,
  "All four headings share one render path; nested Testbild/Intervjun must not repeat AI badges");
assert.ok(overall.includes('box.appendChild(el("h6", "after-interview-overall__subheading", subtitle))'));
assert.ok(overall.includes('!hasRawSourceLeak(section)'), "Never badge malformed model output");

// The badge itself never changes its visible name to 'AI-assisterat'.
assert.ok(badges.includes('return isSwedish() ? "AI-genererat" : "AI-generated";'));
assert.ok(!badges.includes('"AI-assisterat"'));
assert.ok(!badges.includes('"AI-assisted"'));
// Manager Personality includes generated Tips for trivsel; Skills and
// Motivation are Sova-derived/static and must not be mislabelled as AI.
assert.ok(badges.includes('const sources = [personality, wellbeing].filter(Boolean)'));
assert.ok(badges.includes('".after-interview-manager-report__personality-title"'));
assert.ok(badges.includes('".after-interview-manager-report__wellbeing-title"'));
assert.ok(badges.includes('false,\n        false,'));
assert.ok(badges.includes('attachPersonalityHelp(badge, hasManualEdit)'));
assert.ok(!badges.includes('[".after-interview-manager-report__skills"'));
assert.ok(!badges.includes('[".after-interview-manager-report__motivation"'));

// Chefsrapport reuses precisely the shared rounded-square buttons, with
// document-download and refresh icons but accessible labels still present.
assert.ok(manager.includes('pdfButton.className = "btn btn-icon btn-light talena-report-action-button after-interview-manager-report__pdf-button"'));
assert.ok(manager.includes('managerReportGenerateButton.className = "btn btn-icon btn-light talena-report-action-button after-interview-manager-report__generate"'));
assert.ok(manager.includes('pdfIcon.setAttribute("viewBox", "0 0 24 24")'));
assert.ok(manager.includes('managerReportGenerateIcon.setAttribute("data-feather", "refresh-cw")'));
assert.ok(manager.includes('pdfLabel.className = "visually-hidden"'));
assert.ok(manager.includes('managerReportGenerateLabel.className = "visually-hidden"'));
assert.ok(manager.includes('managerReportActions.appendChild(pdfButton)'));
assert.ok(manager.includes('managerReportActions.appendChild(managerReportGenerateButton)'));
assert.ok(manager.includes('pdfButton.replaceChildren(spinner, pdfLabel)'));
assert.ok(manager.includes('managerReportGenerateButton.replaceChildren(spinner, managerReportGenerateLabel)'));
assert.ok(manager.includes('renderElementAsPdf(printableReport, filename, outputRoot)'));
assert.ok(manager.includes('managerReportGenerateButton.addEventListener("click", async () => {'));
assert.ok(actionsCss.includes('.talena-report-action-button.btn-icon') &&
  actionsCss.includes('width:42px !important') &&
  actionsCss.includes('height:42px !important') &&
  actionsCss.includes('border-radius:12px !important'));
assert.ok(shell.includes('three-ai-headings-v2'));
assert.ok(shell.includes('manager-icon-actions-v12'));
assert.ok(processHeader.includes('ai-generated-only-v4'));
console.log("AI-only provenance labels and 42px manager icon actions contract passed.");
