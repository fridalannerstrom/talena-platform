"use strict";
// #442: remove the visual/automatic Interview summary only; preserve history.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const read = path => fs.readFileSync(path, "utf8");
const tabs = read("static/js/talena/after-interview-tabs.js");
const labels = read("static/js/talena/candidate-eyebrows.js");
const badges = read("static/js/talena/candidate-ai-badges.js");
const pdfRegistry = read("static/js/talena/candidate-report-export.js");
const template = read("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html");
const ai = read("apps/core/ai/decision_support.py");
const backend = read("apps/processes/interview_question_notes.py");
const shell = read("templates/customer/core/layouts/customer_base.html");
const header = read("templates/customer/processes/_process_header.html");

assert.ok(tabs.includes('const keys = ["evidence", "overview", "explore", "managerReport"]'));
assert.ok(tabs.includes('const reportKeys = keys.filter((key) => key !== "evidence")'));
assert.ok(!tabs.includes('panels.get("interview")'), "Retired summary cannot be rendered as a tab");
assert.ok(!tabs.includes('makeCard(panel, "interview_summary"'),
  "No invisible legacy Interview summary card may remain");
assert.ok(tabs.includes('keys.includes(requested)') &&
  tabs.includes('hasCompiledPostInterviewResult ? "overview" : "evidence"') &&
  tabs.includes('url.searchParams.set(URL_PARAM, initial)'),
  "Old afterTab=interview links must resolve to a current tab");
assert.ok(tabs.includes('copy().tabs.overview') && tabs.includes('copy().tabs.explore'),
  "Keep Helhetsbild and Undersök vidare");
assert.ok(!pdfRegistry.includes('["interview","after-interview"]'),
  "Retired interview summary PDF option must disappear");

const approved = "Här samlas tillgängliga testresultat tillsammans med personens egna perspektiv och konkreta tips för att förstå och använda insikterna i praktiken.";
assert.ok(tabs.includes('managerReportIntro: "' + approved + '"'),
  "Manager-report intro must use exact approved Swedish text");
assert.ok(tabs.includes("assessment results, interview evidence and role context"));
assert.ok(tabs.includes("testresultat, intervjuunderlag och rollkontext"));
assert.ok(labels.includes("testresultat och rollkontext"));
assert.ok(!labels.includes("testresultat och processkontext"),
  "Remove the old user-visible processkontext in After interview copy");

assert.ok(ai.includes("POST_INTERVIEW_CONTENT_BLOCK_KEYS = (") &&
  ai.includes('"interview_summary",  # Legacy: retained for saved history/admin prompts.') &&
  ai.includes('ACTIVE_POST_INTERVIEW_CONTENT_BLOCK_KEYS = (') &&
  ai.includes('"explore_further",') &&
  ai.includes('"wellbeing_tips",'),
  "Historical data and active generation keys must remain distinct");
assert.ok(backend.includes("list(ACTIVE_POST_INTERVIEW_CONTENT_BLOCK_KEYS)") &&
  backend.includes("for key in ACTIVE_POST_INTERVIEW_CONTENT_BLOCK_KEYS") &&
  backend.includes("if block_key and block_key not in ACTIVE_POST_INTERVIEW_CONTENT_BLOCK_KEYS"),
  "The retired block must not be generated, required or regenerated directly");
assert.ok(ai.includes('for key in ACTIVE_POST_INTERVIEW_CONTENT_BLOCK_KEYS'),
  "New content completion must ignore the historic summary");
assert.ok(template.includes('data-after-interview-block="interview_summary"'),
  "Older saved summaries must remain readable for history/legacy storage");

assert.ok(badges.includes(".after-interview-tab-card__header .after-interview-tab-card__title") &&
  badges.includes('data-after-interview-ai-origin="true"') &&
  !badges.includes('block.querySelectorAll(".after-interview-rich-text__heading")'),
  "One AI provenance badge per generated report, not each Markdown heading");
assert.ok(badges.includes('".after-interview-manager-report__personality-title"') &&
  badges.includes('".after-interview-manager-report__wellbeing-title"') &&
  badges.includes('field.dataset.managerReportManuallyEdited === "true"') &&
  badges.includes('personality?.querySelector(') &&
  badges.includes('setBadge(') &&
  badges.includes('hasAi,') &&
  badges.includes('hasManualEdit,'),
  "Single AI provenance badge covers Personality and Wellbeing; preserve manual-edit provenance");
assert.ok(!badges.includes('field.parentNode.insertBefore(badge, field)'),
  "Do not repeat an AI badge for every manager personality paragraph");
assert.ok(shell.includes("ticket442-v11") && shell.includes("retired-summary-v4"));
assert.ok(header.includes("rolecontext-v6") && header.includes("428-personality-help-v3"));
console.log("Ticket #442: retired tab, legacy preservation, approved copy and quieter AI badges passed.");
