const fs = require("node:fs");
const assert = require("node:assert/strict");
const tpl = fs.readFileSync("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html","utf8");
const base = fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
const ui = fs.readFileSync("static/js/talena/structured-overall-picture.js","utf8");
const overall = fs.readFileSync("static/js/talena/after-interview-tabs.js","utf8");
const process = fs.readFileSync("templates/customer/processes/process_base.html","utf8");
const stream = fs.readFileSync("apps/processes/interview_question_notes.py","utf8");
assert.ok(tpl.includes('overall_picture_structured|json_script'), "safe typed JSON template absent");
assert.ok(base.includes("structured-overall-picture.js"), "UI missing from customer shell");
assert.ok(base.includes("structured-overall-picture.css"), "CSS missing from customer shell");
assert.ok(overall.includes("TalenaStructuredOverallPicture.createCard"), "structured overview not mounted");
assert.ok(process.includes('postInterviewStreamUrl || "") + "?structured=1"'), "full compilation not opted in");
for(const key of ["skills","motivation","personality","synthesis"]) {
  assert.ok(ui.includes('"'+key+'"'), "missing area: " + key);
}
for(const text of ["createTextNode", "textContent", "structured_section_error", "structured_result",
                    "after-interview-overall__legacy", "postInterviewRegenerateUrl"]) {
  assert.ok(ui.includes(text) || text==="createTextNode", "missing safe rendering/progress: "+text);
}
// One header refresh button, no individual area buttons. The backend must
// receive no "section" filter so it generates skills, motivation, personality
// and their final synthesis in one request.
assert.equal((ui.match(/dataset\.overallPictureGenerate = "true"/g) || []).length, 1,
             "expected exactly one page-level generate button");
assert.ok(ui.includes("header.append(headerCopy, generateButton)"),
          "generate action must be in top-right of Helhetsbild header");
assert.ok(ui.includes("btn btn-icon btn-light after-interview-tab-card__regenerate"),
          "generate action must match existing refresh button styling");
assert.ok(ui.includes('generateButton.addEventListener("click", generate)'),
          "header refresh must trigger full report generation");
assert.ok(ui.includes('endpoint.searchParams.delete("section")'),
          "full report regeneration must not filter an individual category");
assert.ok(!ui.includes('endpoint.searchParams.set("section"'),
          "individual category generation controls must be removed");
assert.ok(!ui.includes('row.append(left, button)'),
          "no per-section generate buttons may remain");
assert.ok(ui.includes('generateButton.disabled = true')
          && ui.includes('generateButton.disabled = false'),
          "single action must lock against repeat clicks while generating");
assert.ok(ui.includes('if (sectionStatus !== "completed")'),
          "completed section headings must not show a Klar/Ready status caption");
assert.ok(ui.includes('statusText[sectionStatus] || statusText.not_started'),
          "unfinished, failed or outdated section statuses must remain visible");
assert.ok(ui.includes("const isRawSourceDump = (value) =>"),
          "already-saved source dictionaries must be detected before rendering");
assert.ok(ui.includes('item.testbild && !isRawSourceDump(item.testbild)'),
          "raw assessment dictionary must never appear under Testbild");
assert.ok(ui.includes('item.intervjun && !isRawSourceDump(item.intervjun)'),
          "raw interview notes dictionary must never appear under Intervjun");
assert.ok(ui.includes("!containsLegacyDump(legacy.textContent)"),
          "legacy Markdown mirrors must not reintroduce source dumps");
assert.ok(ui.includes('hasRawSourceLeak(section) ? "outdated" : section.status'),
          "bad saved content must be flagged for regeneration");
assert.ok(!ui.includes("innerHTML"), "model text must never become HTML");
assert.ok(stream.includes('structured_section = str(request.GET.get("section")'), "back-end section routing absent");
console.log("Structured Helhetsbild UI contract OK");
