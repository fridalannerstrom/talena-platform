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

assert.ok(base.includes("js/talena/candidate-report-export.js"));
assert.ok(base.includes("css/talena/pages/candidate-report-export.css"));
assert.ok(base.indexOf("candidate-report-export.js") > base.indexOf("pdf-export-core.js"));
assert.ok(base.indexOf("candidate-report-export.js") > base.indexOf("after-interview-tabs.js"));
assert.ok(css.includes(".talena-candidate-pdf-stage"));
assert.ok(css.includes("left:-10000px"));
assert.ok(core.includes("returnBlob"));
assert.ok(js.includes("window.TalenaCandidateReports = Object.freeze"));
assert.ok(js.includes("getAvailableReports"));
assert.ok(js.includes("async function exportReport(id, options = {})"));
assert.ok(js.includes("if (options.returnBlob) return blob"));
assert.ok(js.includes("returnBlob:true"));
assert.ok(js.includes("document.querySelector(\"[data-candidate-insights-workspace]\")"));
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

// Outside a candidate workspace, the module must be a harmless no-op.
const sandbox = { document: {querySelector: () => null}, window:{} };
vm.runInNewContext(js, sandbox, {timeout:1000});
assert.equal(sandbox.window.TalenaCandidateReports, undefined);
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
const browserDocument = {
  documentElement: {lang: "sv"},
  body: new FakeElement(),
  createElement: tag => new FakeElement(tag),
  querySelector: selector =>
    selector === "[data-candidate-insights-workspace]" ? scope : null
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
const context = {
  document: browserDocument, window: browserWindow,
  MutationObserver: class { observe() {} },
  requestAnimationFrame: callback => callback(),
  URL: {}, console
};
vm.runInNewContext(js, context, {timeout:1000});
(async () => {
  const api = browserWindow.TalenaCandidateReports;
  const listed = api.getAvailableReports();
  assert.equal(listed.length, 1);
  assert.equal(listed[0].id, "overview");
  const blob = await api.exportReport("overview", {returnBlob:true});
  assert.equal(blob.type, "application/pdf");
  assert.equal(rendered, 1);
  await assert.rejects(api.exportReport("motivation-results", {returnBlob:true}));
  console.log("Candidate PDF registry contract and safe Blob export OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
