"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const js = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const html = fs.readFileSync(
  "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html",
  "utf8"
);
const views = fs.readFileSync("apps/processes/views.py", "utf8");

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

const notes = fs.readFileSync("apps/processes/interview_question_notes.py", "utf8");
const comments = fs.readFileSync("apps/core/ai/manager_report_interview_comments.py", "utf8");
const personality = fs.readFileSync("apps/core/ai/manager_report_personality.py", "utf8");

assert.ok(html.includes('manager_report_interview_comments|json_script:"talena-manager-report-interview-comments"'));
assert.ok(!html.includes('manager_motivation_interview_evidence|json_script:'),
  "The manager report must not render raw interview notes as JSON");
assert.ok(js.includes("getManagerInterviewComments(panel)"));
assert.ok(js.includes('makeManagerCommentSection("motivation")'));
assert.ok(js.includes('makeManagerCommentSection("skills")'));
assert.ok(js.includes('key = "interview_comments:" + category'));
assert.ok(js.includes("managerReportEditController.setAiText(key, data.text || \"\")"));
assert.ok(!js.includes("answer.textContent = item.answer"), "No verbatim interview answers may be shown");
assert.ok(!js.includes("evidence.notes.trim()"), "No copy/paste of raw notes in PDF or web UI");
assert.ok(notes.includes('block_key in {"interview_comments:motivation", "interview_comments:skills"}'));
assert.ok(comments.includes("build_manager_report_comment_prompt"));
assert.ok(comments.includes('str(item.get("source") or "").strip().casefold() == source'));
assert.ok(comments.includes("redact_candidate_name"));
assert.ok(comments.includes("visible_manager_report_comments"));
assert.ok(personality.includes('["personality"].strip()'), "Personality AI must use only its own note field");
assert.ok(views.includes('"manager_report_interview_comments"'), "Saved AI comments must be available in both report contexts");

const pdfClone = js.indexOf("const printableReport = managerReportCard.cloneNode(true);");
const reportContents = js.indexOf('managerMotivation.appendChild(makeManagerCommentSection("motivation"))');
assert.ok(pdfClone >= 0 && reportContents > pdfClone, "PDF clones the full report including AI comments");
assert.ok(!js.includes('".after-interview-manager-report__interview-comments,"'),
  "AI comments must remain visible in the PDF");

const guide = js.indexOf("managerSkills.appendChild(guide);");
const reportMotivation = js.indexOf('const managerMotivation = document.createElement("section");');
assert.ok(guide >= 0 && reportMotivation > guide,
  "Keep existing skill cards, guide and section ordering");
assert.ok(js.includes("managerReportEditController.register("),
  "Manager report manual-edit controls must remain intact");
assert.ok(js.includes("managerReportAiTasks.push(async () => {"),
  "Manager AI regeneration tasks must remain intact");
console.log("Ticket #512: AI-polished, source-isolated manager comments, intros and PDF contract OK");
