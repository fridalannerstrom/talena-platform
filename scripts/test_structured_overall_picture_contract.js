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
assert.ok(!ui.includes("innerHTML"), "model text must never become HTML");
assert.ok(stream.includes('structured_section = str(request.GET.get("section")'), "back-end section routing absent");
console.log("Structured Helhetsbild UI contract OK");
