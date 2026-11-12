"use strict";
// Ticket #436: the manager report and AI must use one approved MQ source.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const read = (path) => fs.readFileSync(path, "utf8");
const data = JSON.parse(read("apps/core/ai/reference_data/motivation_practical_advice.json"));
const tabs = read("static/js/talena/after-interview-tabs.js");
const template = read("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html");
const builder = read("apps/core/ai/decision_support.py");
const admin = read("apps/core/ai/prompt_templates.py");
const pdf = read("static/js/talena/pdf-export-core.js");

assert.deepEqual(Object.keys(data).sort(), ["en", "sv"]);
const keys = Object.keys(data.sv);
assert.equal(keys.length, 20);
assert.deepEqual(keys.slice().sort(), Object.keys(data.en).sort());
for (const lang of ["sv", "en"]) {
  for (const [key, group] of Object.entries(data[lang])) {
    assert.equal(group.do.length, 2, lang + "/" + key + ": do");
    assert.equal(group.avoid.length, 2, lang + "/" + key + ": avoid");
  }
}
assert.ok(template.includes("{% load i18n motivation_practical_advice %}"));
assert.ok(template.includes('json_script:"talena-motivation-practical-advice"'));
assert.ok(tabs.includes('getMotivationPracticalAdvice(panel)'));
assert.ok(tabs.includes('JSON.parse(source.textContent || "{}")'));
assert.ok(!tabs.includes("const MOTIVATION_PRACTICAL_ADVICE = {"),
  "JS must not retain a second copy of approved advice.");
assert.ok(tabs.includes('managerPersonalityAdviceTitle: "Tips för trivsel"'));
assert.ok(tabs.includes('managerPersonalityAdviceTitle: "Wellbeing tips"'));
assert.ok(tabs.includes('managerAdvice.className = "after-interview-manager-report__wellbeing"'));
assert.ok(tabs.includes('managerAdviceBody,\n      "wellbeing_tips"'));
assert.ok(tabs.includes('managerReportCard.appendChild(managerAdvice)'));
assert.ok(!tabs.includes('managerPersonality.appendChild(managerAdvice)'));
assert.equal((tabs.match(/managerReportCard\.appendChild\(managerAdvice\)/g) || []).length, 1,
  "The wellbeing block must be present exactly once.");
assert.ok(tabs.includes('sourceContent(panel, "wellbeing_tips")'));
assert.ok(tabs.includes('managerReportEditController.register('));
assert.ok(tabs.includes('"wellbeing_tips",\n        managerAdviceBody'));
assert.ok(pdf.includes(".after-interview-manager-report__wellbeing"));
assert.ok(builder.includes('if block_key == "wellbeing_tips"'));
assert.ok(builder.includes('_build_wellbeing_tips_reference_evidence(owner, language_code=language_code)'));
assert.ok(builder.includes('[:3]'));
assert.ok(builder.includes('get_motivation_practical_advice()[language]'));
assert.ok(builder.includes('build_owner_personality_ai_evidence(owner, language_code=language)'));
assert.ok(admin.includes('post_interview_wellbeing_tips'));
console.log("Wellbeing #436 shared guidance, prompt and manager report contract passed.");
