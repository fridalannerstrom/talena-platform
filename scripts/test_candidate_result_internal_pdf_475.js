"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = name => fs.readFileSync(name, "utf8");
const content = read("apps/candidate_results/content.py");
const presentation = read("apps/candidate_results/presentation.py");
const access = read("apps/candidate_results/views.py");
const email = read("apps/candidate_results/email.py");
const tab = read("templates/candidate_results/_candidate_result_tab.html");
const preview = read("templates/candidate_results/result.html");
const pdf = read("static/js/talena/candidate-result-internal-pdf.js");
const shell = read("templates/customer/core/layouts/customer_base.html");

assert.ok(
  !content.includes('if not invitation.process.candidate_results_enabled:\n        raise ValueError'),
  "Static snapshot creation must not require candidate sharing",
);
assert.ok(presentation.includes('invitation.status == "completed"'), "Only completed results can create reports");
assert.ok(presentation.includes("create_candidate_result_snapshot("), "Internal snapshot must be created if absent");
assert.ok(access.includes("if not access.snapshot.process.candidate_results_enabled or not access.is_active(now):"),
  "Public candidate report still requires enabled sharing and valid access");
assert.ok(email.includes('if not invitation.process.candidate_results_enabled:'),
  "Email delivery must remain conditional on sharing");
assert.ok(tab.includes("data-candidate-result-download") && tab.includes("candidate_result_preview_url"),
  "Internal candidate report must expose authorised PDF download");
assert.ok(preview.includes("{% if preview %}") && preview.includes("data-candidate-result-pdf-button"),
  "Only internal preview gets PDF controls");
assert.ok(pdf.includes("TalenaPdfExport.exportSections") && pdf.includes("data-candidate-result-internal-preview"),
  "Reuse Talena PDF engine on protected preview content");
assert.ok(shell.includes("candidate-result-internal-pdf.js"),
  "The internal download action must be available in dynamic candidate tabs");
assert.ok(!pdf.includes("candidate_results_enabled") && !pdf.includes("send_candidate_result_email"),
  "Downloading cannot enable sharing or send email");

console.log("Ticket #475 internal candidate-report PDF contracts passed.");
