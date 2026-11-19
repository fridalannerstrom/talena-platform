"use strict";
// #359: source contract for the current-candidate PDF registry.
// Browser rendering and PDF page layout also require manual visual QA.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = path => fs.readFileSync(path, "utf8");
const js = read("static/js/talena/candidate-report-export.js");
const css = read("static/css/talena/pages/candidate-report-export.css");
const base = read("templates/customer/core/layouts/customer_base.html");
const core = read("static/js/talena/pdf-export-core.js");
const processBase = read("templates/customer/processes/process_base.html");

assert.ok(base.includes("js/talena/candidate-report-export.js"));
assert.ok(base.includes("css/talena/pages/candidate-report-export.css"));
assert.ok(base.indexOf("candidate-report-export.js") > base.indexOf("pdf-export-core.js"));
assert.ok(base.indexOf("candidate-report-export.js") > base.indexOf("after-interview-tabs.js"));
assert.ok(css.includes(".talena-candidate-pdf-stage"));
assert.ok(js.includes('source.querySelector(".ai-overview-header__actions")'),
  "Overview PDF icon must be inserted beside Generate");
assert.ok(js.includes('button.innerHTML = pdfIcon'),
  "Export action must use the compact PDF icon");
assert.ok(js.includes('stage.setAttribute("data-candidate-pdf-report", item.id)'),
  "Temporary PDF stage must expose report identity for A4 layout styling");
assert.ok(css.includes(".talena-candidate-pdf-toolbar--overview"),
  "Overview action-row styles are missing");
assert.ok(js.includes('const generateSelector = [') &&
  js.includes('source.querySelector(generateSelector)') &&
  js.includes('pair.append(toolbar, generate)'),
  "PDF and Generate must render side by side in the same action pair");
assert.ok(js.includes('"[data-overall-picture-generate]"') &&
  js.includes('["overview","after-overview"]'),
  "Structured Helhetsbild must share its action pair with the PDF button");
assert.ok(js.includes('"[data-after-interview-regenerate]"') &&
  js.includes('source.querySelector(generateSelector)') &&
  js.includes('pair.append(toolbar, generate)'),
  "Active After interview reports must pair PDF and refresh in their title toolbar");
assert.ok(!js.includes('["interview","after-interview"]'),
  "Retired Interview summary must not be offered as a PDF option");
// #483: Svarsstilar is the dedicated Personality results subtab.
// Regression: the three personality reports are sourced from the exact
// subview nodes, including inactive [hidden] quick and summary panels.
for (const [id, selector, marker] of [
  ["personality-detailed-results", "#personality-detailed-view", ".personality-trait-card"],
  ["personality-quick-results", "#personality-quick-view", ".personality-quick-row"],
  ["personality-summary-results", "#personality-descriptions-view", ".personality-description-quick-row"]
]) {
  assert.ok(js.includes('id: "' + id + '", packageOnly: true') &&
    js.includes('selector: "' + selector + '"'),
    "The package needs three independent source selectors");
  assert.ok(js.includes('element.querySelector("' + marker + '")'),
    "Do not expose empty personality report: " + id);
}
assert.ok(js.includes('if (item.existingButton || item.packageOnly) return') &&
  js.includes('if (item.packageOnly) return'),
  "Package-only personality exports must not add stray buttons in candidate results");
assert.ok(js.includes('["personality-results", "personality-quick-results"].includes(reportId)'),
  "Both original and package-only quick charts need the correct midpoint-to-score colours");
assert.ok(core.includes('"personality-detailed-results"') &&
  core.includes('"personality-quick-results"') &&
  core.includes('"personality-summary-results"'),
  "Use the existing detailed, quick and summary paginators respectively");
for (const id of [
  "personality-detailed-results", "personality-quick-results", "personality-summary-results"
]) {
  assert.ok(css.includes('data-candidate-pdf-report="' + id + '"'),
    "PDF styles must account for each personality result subtype");
}
const personalityPage = read("templates/customer/processes/partials/candidate_insights/personality/_results.html");
const responseContent = read("templates/customer/processes/partials/candidate_insights/personality/_response_styles_content.html");
assert.ok(personalityPage.includes('id="personality-response-styles-view"') &&
  personalityPage.includes('personality/_response_styles_content.html'));
assert.ok(js.includes('id: "personality-response-styles"') &&
  js.includes('selector: "#personality-response-styles-view"'));
assert.ok(js.includes('!element.querySelector("[data-response-styles-unavailable]")'),
  "No empty Response styles report when no results exist");
assert.ok(responseContent.includes('{% trans "Response styles" %}') &&
  responseContent.includes('Möjliga nyanser att utforska'));
const beforeInterviewQuestions = read("templates/customer/processes/partials/candidate_insights/tabs/_questions.html");
assert.ok(beforeInterviewQuestions.includes("data-combined-questions-root") &&
  beforeInterviewQuestions.includes("combined-question-sections") &&
  beforeInterviewQuestions.includes("_interview_static_questions.html") &&
  beforeInterviewQuestions.includes("section.questions"),
  "All opening and saved Personality/Motivation/Skills interview questions share one source");
assert.ok(js.includes('id: "combined-interview-questions"') &&
  js.includes('selector: "#candidate-insights-panel-prepare-interview [data-combined-questions-root]"'),
  "Combined questions must be an independent PDF entry sourced only from Before interview questions");
assert.ok(js.indexOf('id: "combined-interview-questions"') >
  js.indexOf('id: "personality-response-styles"'),
  "All interview questions must follow Svarsstilar");
assert.ok(js.includes('element.querySelector(".personality-question-card, .interview-static-questions__item")'),
  "Do not offer the combined question PDF if no questions are present");
assert.ok(!js.includes('clone.append(questions)') &&
  !js.includes('talena-response-styles-interview-questions'),
  "Svarsstilar must not duplicate all interview questions in its own PDF");
assert.ok(js.includes('"combined-interview-questions"].includes(reportId)'),
  "The separate question report must use the existing PDF cleanup for notes and labels");
assert.ok(core.includes('combinedInterviewQuestionsPdf') &&
  core.includes('getMotivationQuestionsPageGuides(opts.node, source)'),
  "Interview question cards should remain intact across PDF page breaks");
assert.ok(css.includes('data-candidate-pdf-report="combined-interview-questions"') &&
  css.includes(".talena-candidate-pdf-heading"),
  "Use the native combined interview questions heading in the PDF");
const afterInterviewCards = read("static/js/talena/after-interview-tabs.js");
assert.ok(afterInterviewCards.includes('button.dataset.afterInterviewRegenerate = blockKey;') &&
  afterInterviewCards.includes('toolbar.appendChild(button);') &&
  afterInterviewCards.includes('toolbar.className = "after-interview-tab-card__toolbar"'),
  "The inline refresh button must remain attached to the report heading toolbar");
assert.ok(js.includes('findHeading(source)') &&
  js.includes('header.append(toolbar)'),
  "Results PDF must be inside the report heading, not a separate top row");
assert.ok(js.includes('toolbar.classList.add("talena-candidate-pdf-toolbar--inline")'),
  "Inline toolbar styling must be used on heading and Generate pairs");
assert.ok(css.includes(".talena-candidate-report-button-pair") &&
  css.includes("border-radius:12px !important") &&
  css.includes("width:42px !important") &&
  css.includes("height:42px !important"),
  "Paired Generate/PDF buttons must have matching rounded-square geometry");
assert.ok(js.includes('width="19" height="19"') &&
  js.includes('stroke-width="1.75"'),
  "PDF icon should remain legible but subtle at 19px with a light stroke");
assert.ok(css.includes("width:19px !important") && css.includes("stroke-width:1.75"),
  "Both PDF and Generate icons should use the same subtle sizing");
assert.ok(css.includes(".personality-questions-header.mt-4"),
  "Nested question headings need compact spacing after the tab row");
assert.ok(css.includes(".personality-trait-card__main") &&
  css.includes(".personality-indicator-row__profile"),
  "Personality PDF needs explicit A4-width chart grids");

// Regression: the original 12-page PDF lost every right-hand indicator
// scale half because [aria-hidden=true] removed the 1px grid centre-line.
// The centre-line is a *visible* layout spacer, not hidden PDF content.
const cloneRemoveSelector = js.match(/clone\.querySelectorAll\(\s*'button, form, input[\s\S]*?\)\.forEach\(element => element\.remove\(\)\);/);
assert.ok(cloneRemoveSelector, "PDF clone cleanup selector must remain testable");
assert.ok(!cloneRemoveSelector[0].includes('[aria-hidden="true"]'),
  "aria-hidden must not remove the indicator centre-line/right five STEN steps");
assert.ok(core.includes(".personality-indicator-row"),
  "PDF pager must recognize indicator rows as natural breakpoints");
assert.ok(core.includes(".personality-trait-card__main"),
  "PDF pager must recognize larger trait charts as natural breakpoints");
assert.ok(css.includes("left:-10000px"));
assert.ok(core.includes("returnBlob"));
assert.ok(js.includes("window.TalenaCandidateReports = Object.freeze"));
assert.ok(js.includes("getAvailableReports"));
assert.ok(js.includes("async function exportReport(id, options = {})"));
assert.ok(js.includes("if (options.returnBlob) return blob"));
assert.ok(js.includes("returnBlob:true"));
assert.ok(js.includes('container.querySelector?.("[data-candidate-insights-workspace]")'));
assert.ok(js.includes("initialize(document)"));
assert.ok(js.includes("observer?.disconnect()"));
assert.ok(processBase.includes("TalenaCandidateReports?.initialize?.(container)"));
assert.ok(js.includes("workspace.querySelector(item.selector)"));
assert.ok(js.includes("if (!item || !isReady(item)) throw Error(copy.unavailable)"));
for (const id of [
  "overview", "personality", "motivation", "cognitive", "team-report",
  "leadership-report", "derailment-report", "personality-response-styles", "prepare-interview",
  "after-overview", "manager-report"
]) {
  assert.ok(js.includes(id), "Registry missing " + id);
}
for (const marker of [
  "cloneNode(true)", 'clone.querySelectorAll("canvas")',
  'clone.querySelectorAll("details")',
  "[data-candidate-pdf-toolbar]", "data-has-result", "outdated",
  'button, form, input, textarea, select', "new MutationObserver(schedule)"
]) {
  assert.ok(js.includes(marker), "Missing content/readiness safeguard " + marker);
}
assert.ok(!/\bfetch\s*\(/.test(js), "PDF export must not make candidate/API requests");
assert.ok(!/\bpostMessage\s*\(/.test(js), "PDF export must not post data elsewhere");
assert.ok(!js.includes("window.open("), "PDF export must stay in the current authorised context");

// Before an AJAX candidate sheet is injected, the registry API is available
// but must not expose any candidate's content.
const sandbox = { document: {documentElement: {lang:"sv"}, querySelector: () => null}, window:{} };
vm.runInNewContext(js, sandbox, {timeout:1000});
assert.ok(sandbox.window.TalenaCandidateReports);
assert.deepEqual(Array.from(sandbox.window.TalenaCandidateReports.getAvailableReports()), []);
// A small browser-shaped runtime check verifies that only the current
// authorised workspace can be exported and Blob mode never downloads.
class FakeElement {
  constructor(tag = "div", content = "") {
    this.tag = tag;
    this.textContent = content;
    this.children = [];
    this.dataset = {};
    this.attributes = [];
    this.hidden = false;
    this.style = {setProperty() {}};
    this.classList = {contains: () => false, remove() {}, add() {}};
  }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  closest() { return null; }
  cloneNode() { return new FakeElement(this.tag, this.textContent); }
  removeAttribute() {}
  setAttribute() {}
  remove() {}
  append(...children) { this.children.push(...children); }
  insertBefore(node) { this.children.unshift(node); }
  addEventListener() {}
}
const overview = new FakeElement("section", "Synthetic assessment results ".repeat(20));
const scope = new FakeElement();
// The visible heading can fall back to email, but the dedicated filename
// attribute contains *only* the candidate's first and last name.
const candidateIdentity = {
  textContent: "private-email@example.invalid",
  getAttribute: attr => attr === "data-report-export-name" ? "Anna Andersson" : null
};
scope.closest = selector => selector === ".candidate-sheet-layout"
  ? {querySelector: childSelector =>
      childSelector === ".candidate-profile-name[data-report-export-name]"
        ? candidateIdentity : null} : null;
scope.querySelector = selector =>
  selector === "#candidate-insights-panel-overview" ? overview : null;
let currentWorkspace = null; // Model dynamically opened candidate offcanvas.
const browserDocument = {
  documentElement: {lang: "sv"},
  body: new FakeElement(),
  createElement: tag => new FakeElement(tag),
  querySelector: selector =>
    selector === "[data-candidate-insights-workspace]" ? currentWorkspace : null
};
let rendered = 0;
const browserWindow = {
  TalenaPdfExport: {
    exportSections: async (_sections, options) => {
      assert.equal(options.returnBlob, true);
      rendered += 1;
      return {type: "application/pdf", bytes: 42};
    }
  }
};
let disconnected = 0;
const context = {
  document: browserDocument, window: browserWindow,
  MutationObserver: class { observe() {} disconnect() { disconnected += 1; } },
  requestAnimationFrame: callback => callback(),
  URL: {}, console
};
vm.runInNewContext(js, context, {timeout:1000});
(async () => {
  const api = browserWindow.TalenaCandidateReports;
  assert.equal(api.getAvailableReports().length, 0);
  currentWorkspace = scope;
  api.initialize(browserDocument);
  const listed = api.getAvailableReports();
  assert.equal(listed.length, 1);
  assert.equal(listed[0].id, "overview");
  assert.equal(listed[0].filename, "Anna Andersson - Överblick.pdf");
  assert.equal(api.getPackageFilename("pdf"), "Anna Andersson - Rapportpaket.pdf");
  assert.equal(api.getPackageFilename("zip"), "Anna Andersson - Rapporter.zip");
  assert.ok(!listed[0].filename.includes("private-email"));
  candidateIdentity.getAttribute = () => "Åsa / \u202EAndersson:Test";
  assert.equal(api.getPackageFilename("zip"), "Åsa Andersson Test - Rapporter.zip",
    "Filename must preserve Swedish letters and strip unsafe filename characters");
  candidateIdentity.getAttribute = () => "Anna Andersson";
  const blob = await api.exportReport("overview", {returnBlob:true});
  assert.equal(blob.type, "application/pdf");
  assert.equal(rendered, 1);
  await assert.rejects(api.exportReport("motivation-results", {returnBlob:true}));

  const second = new FakeElement();
  second.querySelector = selector => selector === "#candidate-insights-panel-overview"
    ? new FakeElement("section", "Next candidate has no completed results.") : null;
  currentWorkspace = second;
  api.initialize(browserDocument);
  assert.equal(api.getPackageFilename("pdf"), "talena-rapportpaket.pdf",
    "Missing names must not fall back to an email or previous candidate");
  assert.equal(disconnected, 1, "The old candidate observer must be stopped");
  assert.equal(api.getAvailableReports().length, 0,
    "An incomplete second candidate must not inherit previous report exports");
  await assert.rejects(api.exportReport("overview", {returnBlob:true}));

  // #483: two distinct report selections in the correct order. The PDF
  // export must not combine them or leak a previous candidate's content.
  const responseStyles = new FakeElement("section", "Svarsstilar: statiskt resultat");
  responseStyles.querySelector = selector =>
    selector === ".response-styles-header" ? {} : null;
  const questions = new FakeElement("section",
    "Alla intervjufrågor: inledande, personlighet, motivation, färdighet");
  questions.querySelector = selector =>
    [".combined-question-sections",
      ".personality-question-card, .interview-static-questions__item"].includes(selector)
      ? {} : null;
  const third = new FakeElement();
  third.querySelector = selector =>
    selector === "#personality-response-styles-view" ? responseStyles
    : selector === "#candidate-insights-panel-prepare-interview [data-combined-questions-root]"
      ? questions : null;
  let exportedContent;
  browserWindow.TalenaPdfExport.exportSections = async (sections, options) => {
    assert.equal(options.returnBlob, true);
    exportedContent = sections[1].node.children[1];
    rendered += 1;
    return {type:"application/pdf", bytes:42};
  };
  currentWorkspace = third;
  api.initialize(browserDocument);
  assert.deepEqual(Array.from(api.getAvailableReports()).map(report => report.id),
    ["personality-response-styles", "combined-interview-questions"]);
  assert.equal(api.getAvailableReports()[1].title, "Alla intervjufrågor");

  await api.exportReport("personality-response-styles", {returnBlob:true});
  assert.equal(exportedContent.textContent, responseStyles.textContent);
  assert.equal(exportedContent.children.length, 0,
    "Svarsstilar must remain separate, without appended interview questions");

  await api.exportReport("combined-interview-questions", {returnBlob:true});
  assert.equal(exportedContent.textContent, questions.textContent);
  assert.equal(exportedContent.children.length, 0,
    "All interview questions PDF should contain only its own question root");

  // The question option disappears if nothing has been generated or configured.
  questions.querySelector = selector =>
    selector === ".combined-question-sections" ? {} : null;
  assert.deepEqual(Array.from(api.getAvailableReports()).map(report=>report.id),
    ["personality-response-styles"]);
  await assert.rejects(api.exportReport("combined-interview-questions", {returnBlob:true}));
  // Switching the visible Personality tab must never determine which PDF
  // is exported. Each report clones only its own (potentially hidden) source.
  const detailed = new FakeElement("section", "Karaktärsdrags- och indikatorprofil");
  detailed.querySelector = selector => selector === ".personality-trait-card" ? {} : null;
  const quick = new FakeElement("section", "Karaktärsdragsprofil");
  quick.hidden = true;
  quick.querySelector = selector => selector === ".personality-quick-row" ? {} : null;
  const summary = new FakeElement("section", "Resultatsammanfattning");
  summary.hidden = true;
  summary.querySelector = selector => selector === ".personality-description-quick-row" ? {} : null;
  const fourth = new FakeElement();
  fourth.querySelector = selector => ({
    "#personality-detailed-view": detailed,
    "#personality-quick-view": quick,
    "#personality-descriptions-view": summary
  })[selector] || null;
  currentWorkspace = fourth;
  api.initialize(browserDocument);
  assert.deepEqual(Array.from(api.getAvailableReports()).map(report=>report.id), [
    "personality-detailed-results", "personality-quick-results",
    "personality-summary-results"
  ], "Inactive personality result tabs must still be selectable");
  for (const [id, expected] of [
    ["personality-detailed-results", detailed],
    ["personality-quick-results", quick],
    ["personality-summary-results", summary]
  ]) {
    await api.exportReport(id, {returnBlob:true});
    assert.equal(exportedContent.textContent, expected.textContent,
      "Only the requested Personality result view should be exported");
    assert.equal(exportedContent.children.length, 0,
      "Another result tab must never leak into a separate PDF");
  }
  assert.equal(quick.hidden, true, "Export must not activate the live quick tab");
  assert.equal(summary.hidden, true, "Export must not activate the live summary tab");
  summary.querySelector = () => null;
  assert.ok(!api.getAvailableReports().some(report=>report.id==="personality-summary-results"),
    "Empty result summary must not be selected");

  console.log("Candidate PDF registry: candidate isolation, separate Personality views, Svarsstilar and questions OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
