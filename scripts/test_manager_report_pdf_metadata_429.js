/* #429: Both PDF flows use the server-attributed metadata contract. */
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const read = path => fs.readFileSync(path, "utf8");
const helper = read("static/js/talena/manager-report-pdf-metadata.js");
const single = read("static/js/talena/after-interview-tabs.js");
const packageExport = read("static/js/talena/candidate-report-export.js");
const urls = read("apps/processes/urls.py");
const template = read("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html");
const base = read("templates/customer/core/layouts/customer_base.html");

assert.ok(single.includes("window.TalenaManagerReportPdf.prepare(outputRoot)"));
assert.ok(single.includes("window.TalenaManagerReportPdf.decorate(printableReport, reportMetadata)"));
assert.ok(packageExport.includes('if (id === "manager-report")'));
assert.ok(packageExport.includes("window.TalenaManagerReportPdf.prepare(workspace)"));
assert.ok(packageExport.includes("window.TalenaManagerReportPdf.decorate(reportContent, managerReportMetadata)"));
assert.ok(urls.includes('name="process_candidate_manager_report_pdf_prepare"'));
assert.ok(template.includes("data-manager-report-pdf-prepare-url="));
assert.ok(base.includes("js/talena/manager-report-pdf-metadata.js"));

const calls = [];
const existingNodes = [
  {removed:false,remove(){this.removed=true}},
  {removed:false,remove(){this.removed=true}},
  {removed:false,remove(){this.removed=true}}
];
let insertedNote = null;
const sourceNode = {
  querySelectorAll(query) {
    assert.ok(query.includes(".talena-ai-generated-badge"));
    assert.ok(query.includes(".after-interview-manager-report__edited-badge"));
    return existingNodes;
  },
  querySelector(query) {
    return query === ".after-interview-manager-report__intro"
      ? {after(note) {insertedNote = note;}}
      : null;
  }
};
const context = {
  window: {},
  document: {
    cookie: "csrftoken=csrf-test",
    createElement(tag) {
      assert.equal(tag, "p");
      return {className:"",textContent:"",style:{cssText:""}};
    }
  },
  Intl,
  Date,
  Error,
  fetch: async (url, options) => {
    calls.push({url, options});
    return {
      ok: true,
      json: async () => ({
        ok:true,
        language:"sv",
        exported_by:{name:"Johan Svensson",at:"2026-11-07T15:10:00+00:00"},
        last_edited_by:{name:"Anna Andersson",at:"2026-11-07T12:32:00+00:00"}
      })
    };
  }
};
vm.runInNewContext(helper, context);
const root = {dataset:{managerReportPdfPrepareUrl:"/trusted/manager-report-pdf/prepare/"}};
const page = {closest(selector) {
  assert.equal(selector, "[data-final-output-root]");
  return root;
}};
(async () => {
  const meta = await context.window.TalenaManagerReportPdf.prepare(page);
  assert.equal(calls.length,1);
  assert.equal(calls[0].url, "/trusted/manager-report-pdf/prepare/");
  assert.equal(calls[0].options.method,"POST");
  assert.equal(calls[0].options.headers["X-CSRFToken"],"csrf-test");
  assert.equal(calls[0].options.credentials,"same-origin");

  context.window.TalenaManagerReportPdf.decorate(sourceNode, meta);
  assert.ok(existingNodes.every(node => node.removed));
  assert.ok(insertedNote.textContent.includes("Senast redigerad av Anna Andersson"));
  assert.ok(insertedNote.textContent.includes("PDF exporterad av Johan Svensson"));
  assert.equal(insertedNote.textContent.match(/PDF exporterad av/g).length,1);
  assert.ok(insertedNote.style.cssText.includes("font-size:10px"));

  const noEdit = {...meta,last_edited_by:null};
  context.window.TalenaManagerReportPdf.decorate(sourceNode, noEdit);
  assert.ok(!insertedNote.textContent.includes("Senast redigerad"));
  assert.ok(insertedNote.textContent.includes("PDF exporterad av Johan Svensson"));

  const english = {...meta,language:"en"};
  context.window.TalenaManagerReportPdf.decorate(sourceNode, english);
  assert.ok(insertedNote.textContent.includes("Last edited by Anna Andersson"));
  assert.ok(insertedNote.textContent.includes("PDF exported by Johan Svensson"));
  console.log("Manager-report PDF metadata #429 contract OK");
})().catch(error => {console.error(error);process.exitCode=1});
