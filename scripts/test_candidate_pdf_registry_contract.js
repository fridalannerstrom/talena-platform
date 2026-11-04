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
  "leadership-report", "derailment-report", "prepare-interview",
  "after-overview", "after-interview", "after-explore", "manager-report"
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
  const blob = await api.exportReport("overview", {returnBlob:true});
  assert.equal(blob.type, "application/pdf");
  assert.equal(rendered, 1);
  await assert.rejects(api.exportReport("motivation-results", {returnBlob:true}));

  const second = new FakeElement();
  second.querySelector = selector => selector === "#candidate-insights-panel-overview"
    ? new FakeElement("section", "Next candidate has no completed results.") : null;
  currentWorkspace = second;
  api.initialize(browserDocument);
  assert.equal(disconnected, 1, "The old candidate observer must be stopped");
  assert.equal(api.getAvailableReports().length, 0,
    "An incomplete second candidate must not inherit previous report exports");
  await assert.rejects(api.exportReport("overview", {returnBlob:true}));
  console.log("Candidate PDF registry: AJAX sheet and candidate isolation OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
