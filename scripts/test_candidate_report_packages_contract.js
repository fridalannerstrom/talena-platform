"use strict";
// #360 source contracts; real PDFs and visual mobile/browser QA remain mandatory.
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const file=name=>fs.readFileSync(name,"utf8");
const js=file("static/js/talena/candidate-report-packages.js");
const assembler=file("static/js/talena/report-package-core.js");
const css=file("static/css/talena/pages/candidate-report-packages.css");
const registry=file("static/js/talena/candidate-report-export.js");
const base=file("templates/customer/core/layouts/customer_base.html");
assert.ok(base.includes("candidate-report-packages.css"));
assert.ok(base.includes("candidate-report-packages.js"));
assert.ok(base.indexOf("candidate-report-packages.js")>base.indexOf("candidate-report-export.js"));
assert.ok(base.indexOf("report-package-core.js")<base.indexOf("candidate-report-packages.js"),
  "Load shared PDF/ZIP assembler before candidate picker");
assert.ok(registry.includes("exportCover")&&registry.includes("returnBlob:true"));
assert.ok(registry.includes("TalenaReportPackages?.initialize?.(current)"));
assert.ok(js.includes('api().getAvailableReports()'));
assert.ok(js.includes('PACKAGE_ALLOWED_REPORT_IDS.has(r.id)'),
  "The picker must filter the PDF registry with an explicit #483 allowlist");
const packageAllowlist = js.match(/const PACKAGE_ALLOWED_REPORT_IDS = new Set\(\[([\s\S]*?)\]\)/);
assert.ok(packageAllowlist, "The #483 report package allowlist must exist");
const allowedIds = [...packageAllowlist[1].matchAll(/"([^"]+)"/g)].map(match=>match[1]);
assert.deepEqual(allowedIds, [
  "overview",
  "personality-detailed-results", "personality-quick-results",
  "personality-summary-results", "personality-candidate-reflection",
  "motivation-results", "motivation-candidate-reflection",
  "cognitive-results", "cognitive-candidate-reflection",
  "team-report", "leadership-report", "derailment-report",
  "personality-response-styles", "combined-interview-questions"
], "Keep one combined question report, results, Svarsstilar and static reports without AI interpretations");
assert.ok(!allowedIds.some(id=>/(interpretation|after-|manager-report)/.test(id)));
assert.ok(!allowedIds.includes("personality-results"),
  "A single personality result choice must not silently omit inactive tabs");
const personalityIds = [
  "personality-detailed-results", "personality-quick-results", "personality-summary-results"
];
assert.ok(personalityIds.every(id=>allowedIds.includes(id)));
for (const [id, view] of [
  ["personality-detailed-results", "personality-detailed-view"],
  ["personality-quick-results", "personality-quick-view"],
  ["personality-summary-results", "personality-descriptions-view"]
]) {
  assert.ok(registry.includes('id: "'+id+'", packageOnly: true') &&
    registry.includes('selector: "#'+view+'"'),
    "Every personality report must clone its own view independently of the active tab");
}

assert.ok(["personality-questions", "motivation-questions", "cognitive-questions"]
  .every(id => !allowedIds.includes(id)),
  "Per-assessment interview questions must be excluded from the package picker");
assert.equal(allowedIds.filter(id=>id==="combined-interview-questions").length,1,
  "Only the single combined interview questions report may appear in the package");
assert.ok(["personality-questions", "motivation-questions", "cognitive-questions"]
  .every(id => registry.includes('id: area + "-" + part')),
  "Do not remove individual question PDF capabilities from their assessment tabs");
assert.ok(js.includes('managerExcluded:"Chefsrapporten ingår inte i rapportpaketet. Ladda ner den separat."'));
assert.ok(!allowedIds.includes("prepare-interview"),
  "Before-interview must not be offered as Svarsstilar");
assert.ok(registry.includes('id: "personality-response-styles"') &&
  registry.includes('selector: "#personality-response-styles-view"'),
  "Response styles must export the Personality results subtab, not Before interview");
const personalityView = file("templates/customer/processes/partials/candidate_insights/personality/_results.html");
const responseStyles = file("templates/customer/processes/partials/candidate_insights/personality/_response_styles_content.html");
assert.ok(personalityView.includes('id="personality-response-styles-view"') &&
  personalityView.includes('personality/_response_styles_content.html'),
  "The selected report must reuse the actual Personality response styles content");
assert.ok(responseStyles.includes('{% trans "Response styles" %}') &&
  responseStyles.includes('Möjliga nyanser att utforska'),
  "The source tab must contain its own response-style heading and nuances");
const allQuestions = file("templates/customer/processes/partials/candidate_insights/tabs/_questions.html");
assert.ok(allQuestions.includes("data-combined-questions-root") &&
  allQuestions.includes("combined-question-sections") &&
  allQuestions.includes("_interview_static_questions.html") &&
  allQuestions.includes("section.questions"),
  "All questions includes opening questions, Personality, Motivation and Skills");
assert.ok(registry.includes('id: "combined-interview-questions"') &&
  registry.includes('selector: "#candidate-insights-panel-prepare-interview [data-combined-questions-root]"'),
  "The separate report must be sourced from the combined questions, not the Communication strategy");
assert.ok(!registry.includes('clone.append(questions)'),
  "Keep Svarsstilar as an independent report, without duplicated questions");

assert.ok(js.includes('api().exportReport(report.id,{returnBlob:true})'));
assert.ok(js.includes('api().exportCover(t.cover)'));
assert.ok(js.includes('api().getPackageFilename(format)') &&
  js.includes("download(output,packageFilename)"),
  "Both merged PDFs and ZIPs must use the current candidate's download filename");
assert.ok(registry.includes("getPackageFilename") &&
  registry.includes("filename: reportFilename(item)"),
  "Every ZIP entry must be named from the currently authorised candidate");
const candidateSheet = file("templates/customer/processes/_candidate_detail_sheet.html");
assert.ok(candidateSheet.includes('data-report-export-name="{{ candidate.first_name|default:'),
  "Only first and last name may be exposed as report filename metadata");
assert.ok(registry.includes("safeFilenamePart") &&
  registry.includes('data-report-export-name') &&
  registry.includes('document.querySelector?.("[data-candidate-insights-workspace]") !== workspace'),
  "Candidate filename must be sanitised, never use email fallback and be scoped to current sheet");
assert.ok(js.includes('document.querySelector("[data-candidate-insights-workspace]")===workspace'));
assert.ok(js.includes("if(!current()||workspace!==original)throw Error(t.stale)"));
assert.ok(!/\bfetch\s*\(/.test(js),"No candidate/server data may be fetched");
assert.ok(!/\bpostMessage\s*\(/.test(js),"PDF data must not be posted to another origin");
assert.ok(!js.includes("window.open("));
assert.ok(js.includes("dataTransfer.setData")&&js.includes("dragover"));
assert.ok(js.includes("move(id,direction)")&&js.includes(".focus()"));
assert.ok(js.includes("chosen=new Set(on?order:[])"));
assert.ok(js.includes('window.TalenaReportPackageCore.zipFiles(entries)') ||
  js.includes('await core.zipFiles(entries)'),
  "Candidate picker must reuse the shared ZIP assembler");
assert.ok(js.includes('await core.merge(entries,await api().exportCover(t.cover)'),
  "Candidate picker must reuse the shared PDF merger and branded cover");
assert.ok(assembler.includes('window.JSZip')&&assembler.includes('zip.file('));
assert.ok(assembler.includes('window.PDFLib')&&assembler.includes('pdf.copyPages(source,source.getPageIndices())'));
assert.ok(assembler.includes('PDFName.of("Annots")')&&assembler.includes('PDFName.of("Fit")'));
assert.ok(js.includes("MAX_BYTES")&&js.includes("MAX_PAGES")&&js.includes("MAX_REPORTS"));
assert.ok(js.includes("failingReport=report")&&js.includes("failedReportId=failingReport.id"),
  "The picker must identify and mark the individual report that failed");
assert.ok(js.includes("safeFailureHint(err)")&&js.includes("t.combineError"),
  "Report failures must be distinguished from PDF/ZIP assembly failures");
assert.ok(js.includes("await new Promise(resolve=>requestAnimationFrame(resolve))"),
  "Show updated progress before each expensive PDF rendering pass");
assert.ok(css.includes(".talena-package-row.is-failed"),
  "Highlight the failed report so it can be excluded");
assert.ok(base.includes("20261119-combined-questions-only-6"),
  "Version asset URLs to avoid cached report picker code");
assert.ok(js.includes('dialog.showModal()')&&js.includes('dialog.addEventListener("cancel"'));
assert.ok(js.includes('role","status"')&&js.includes('aria-live","polite"'));
assert.ok(js.includes('workspace.closest(".candidate-sheet-layout")') &&
  js.includes('sheet?.querySelector(".candidate-profile-header .candidate-profile-actions")') &&
  js.includes('headerActions.append(trigger)'),
  "Package trigger must live at top right beside candidate name");
assert.ok(js.includes("trigger.parentElement===headerActions"),
  "AJAX refresh must not duplicate a header-level report package button");
assert.ok(!js.includes('nav.append(trigger)'),
  "Report package action must no longer sit inside the Insights navigation");
assert.ok(css.includes(".candidate-profile-header .candidate-profile-actions .talena-package-open") &&
  !css.includes("[data-candidate-insights-workspace] .candidate-insights-navigation {"),
  "Package button CSS must apply to candidate header, not navigation");
assert.ok(css.includes(".talena-package-dialog")&&css.includes(".talena-package-row"));
assert.ok(css.includes('.talena-package-row > input[type="checkbox"]') && css.includes("width:20px") &&
  css.includes("height:20px"), "Package checkboxes must be comfortably sized");
const sandbox={
  document:{documentElement:{lang:"sv"},querySelector:()=>null},
  window:{}
};
vm.runInNewContext(js,sandbox,{timeout:1000});
assert.equal(typeof sandbox.window.TalenaReportPackages.initialize,"function");
console.log("Report package contracts: scoped export, PDF/ZIP, order, TOC links, limits OK");