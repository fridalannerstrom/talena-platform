"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const js = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const html = fs.readFileSync(
  "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html",
  "utf8"
);
const views = fs.readFileSync("apps/processes/views.py", "utf8");
const helper = fs.readFileSync(
  "apps/processes/services/manager_report_motivation_evidence.py", "utf8"
);

const requiredSwedish = [
  "Testresultaten är ett underlag för att skapa en bättre förståelse",
  "Resultaten jämförs med en normgrupp",
  "Ett testresultat är en början, inte hela bilden.",
  "Kandidatens kommentarer bygger på utvalda delar av intervjuunderlaget",
  "Personlighetsformuläret beskriver personens typiska beteenden",
  "Motivationsformuläret beskriver vad som tenderar att ge personen engagemang",
  "Färdighetstestet ger en indikation på hur snabbt och korrekt personen",
];
for (const text of requiredSwedish) {
  assert.ok(js.includes(text), "Manager report must include: " + text);
}
for (const text of [
  "norm group",
  "A test result is a starting point, not the whole picture.",
  "The personality questionnaire describes",
  "The motivation questionnaire describes",
  "The ability assessment indicates",
]) assert.ok(js.includes(text), "English report missing: " + text);

assert.ok(js.includes('const managerReportIntro = document.createElement("div");'));
assert.ok(js.includes('managerReportIntro.className = "after-interview-manager-report__intro"'));
assert.ok(js.includes("managerReportIntroParagraphs.forEach("));
assert.ok(js.includes('managerSkills.append(managerSkillsTitle, makeManagerSectionIntro("skills"));'));
assert.ok(js.includes('managerMotivation.append(managerMotivationTitle, makeManagerSectionIntro("motivation"));'));
assert.ok(js.includes('managerPersonality.append(managerPersonalityTitle, makeManagerSectionIntro("personality"));'));
assert.ok(js.includes("managerSkills.hidden = true;"), "Missing skills must not be presented as a completed area");
assert.ok(js.includes("if (managerMotivators.length) {"), "Motivation requires actual results");
assert.ok(js.includes("if (personalityRoot) {"), "Personality requires actual results");

assert.ok(html.includes('manager_motivation_interview_evidence|json_script:"talena-manager-motivation-interview-evidence"'));
assert.ok(js.includes("getManagerMotivationInterviewEvidence(panel)"));
assert.ok(js.includes("managerMotivation.appendChild(evidenceSection);"));
assert.ok(js.includes("evidence.notes.trim() && !evidence.answers.length"));
assert.ok(js.includes("question.textContent = item.question;"), "The source question must remain attached to the saved answer");
assert.ok(js.includes("answer.textContent = item.answer;"), "Never render raw user HTML");
assert.ok(helper.includes('if item.get("source") == "motivation"'), "No contamination from personality or cognitive");
assert.ok(helper.includes("Old free-form notes have no trustworthy category"));
assert.ok(views.includes('"manager_motivation_interview_evidence"'), "Provide source in both main and refreshed report");

const pdfClone = js.indexOf("const printableReport = managerReportCard.cloneNode(true);");
const reportContents = js.indexOf("managerMotivation.appendChild(evidenceSection)");
assert.ok(pdfClone >= 0 && reportContents > pdfClone, "PDF clones the complete live report");
assert.ok(!js.includes('".after-interview-manager-report__motivation-evidence,"'),
  "Saved interview evidence must remain in the PDF, not be filtered");

const guide = js.indexOf("managerSkills.appendChild(guide);");
const reportMotivation = js.indexOf('const managerMotivation = document.createElement("section");');
assert.ok(guide >= 0 && reportMotivation > guide,
  "Keep existing skill cards, guide and section ordering");
assert.ok(js.includes("managerReportEditController.register("),
  "Manager report manual-edit controls must remain intact");
assert.ok(js.includes("managerReportAiTasks.push(async () => {"),
  "Manager AI regeneration tasks must remain intact");
console.log("Ticket #512: source-backed Motivation, intros and shared PDF contract OK");
