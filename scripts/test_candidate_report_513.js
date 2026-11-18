"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const content = fs.readFileSync("apps/candidate_results/content.py", "utf8");
const report = fs.readFileSync("templates/candidate_results/result.html", "utf8");
const view = fs.readFileSync("apps/candidate_results/views.py", "utf8");
const presentation = fs.readFileSync("apps/candidate_results/presentation.py", "utf8");
const admin = fs.readFileSync("apps/accounts/views.py", "utf8");
const pdf = fs.readFileSync("static/js/talena/candidate-result-internal-pdf.js", "utf8");

const titles = [
  "Samarbete och relationer",
  "Hjälpsamhet och finnas där för andra",
  "Påverka andra och komma framåt",
  "Planering och målfokus",
  "Analys och strategi",
  "Förändring och nytänkande",
  "Kommunikationsstil och principfasthet",
  "Att synas eller smälta in",
  "Stress och press",
  "Självständigt arbete och förankring",
];
for (const title of titles) {
  assert.ok(content.includes(title), "Missing candidate personality heading: " + title);
}
assert.ok(content.includes('(("Straightforward",),'), "Honesty and rule orientation must be one trait");
assert.ok(content.includes('(("Independence",),'), "Independence must be one trait");
assert.ok(content.includes('CANDIDATE_RESULT_CONTENT_VERSION = "candidate-static-v6-513"'),
  "Static report snapshot needs safe refresh to display the new headings");
assert.ok(content.includes("CANDIDATE_PERSONALITY_TOPICS[_section[\"section_key\"]]"),
  "Each of the 18 traits must be accounted for by an explicit topic");
assert.ok(content.includes('"label": title_sv if language_code == "sv" else title_en'),
  "Topic labels should match the snapshot locale");
assert.ok(content.includes('content[section_key]["introduction"]'), "Only included test areas get introductions");

for (const text of [
  "Testresultaten är ett underlag för att skapa en bättre förståelse",
  "Dina resultat jämförs med en ",
  '"norm_emphasis": "normgrupp"',
  "Ett testresultat är en början, inte hela bilden.",
  "Om du vill kan du lämna en kommentar till ditt resultat",
  "Personlighetsformuläret beskriver dina typiska beteenden",
  "Motivationsformuläret beskriver vad som tenderar att ge dig engagemang",
  "Färdighetstestet ger en indikation på hur snabbt och korrekt du hanterar",
]) {
  assert.ok(content.includes(text), "Missing approved candidate introduction: " + text);
}
assert.ok(report.includes("<p>{{ introduction.comment_candidate }}</p>") &&
  !report.includes("{{ introduction.comment_preview }}"),
  "Admin/PDF preview must show the same introduction as the candidate");
assert.ok(report.includes("{{ introduction.comment_candidate }}") &&
  report.includes("data-feedback-choice="), "Candidate feedback UI remains available");
assert.ok(report.includes("<strong>{{ introduction.norm_emphasis }}</strong>") &&
  report.includes("<strong>{{ introduction.caveat_emphasis }}</strong>"),
  "Important words must be emphasized in both web and PDF");
assert.ok(report.includes('class="section-introduction"'), "Test-specific copy must be rendered");
assert.ok(view.includes('"introduction": str(section.get("introduction") or "").strip()'),
  "Shared result context must expose test-specific intros");
assert.ok(presentation.includes('invitation.status == "completed"') &&
  presentation.includes("create_candidate_result_snapshot("),
  "Internal report must remain accessible even if candidate sharing is off");
assert.ok(admin.includes('"is_admin_candidate_mirror": True') &&
  admin.includes("ctx = build_candidate_detail_context("),
  "Admin preview must reuse the customer's report context");
assert.ok(pdf.includes("const stage = root.cloneNode(true);") &&
  pdf.includes('.hero-card, .intro-card, .section-card'),
  "Export must include the same sections, topic headings and intro copy");
assert.ok(!pdf.includes("send_candidate_result_email"), "Preview/PDF must not send email");
console.log("Ticket #513 candidate report structure and privacy contract: OK");
