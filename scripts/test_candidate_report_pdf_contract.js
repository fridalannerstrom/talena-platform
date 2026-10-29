// #359: focused registry / tenant-scoped rendering / no-AI export tests.
"use strict";
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

const code = fs.readFileSync("static/js/talena/candidate-report-pdf.js", "utf8");
const workspaceHtml = fs.readFileSync("templates/customer/processes/partials/candidate_insights/_workspace.html", "utf8");
const context = fs.readFileSync("apps/processes/views.py", "utf8");
const layout = fs.readFileSync("templates/customer/core/layouts/customer_base.html", "utf8");
const processJs = fs.readFileSync("templates/customer/processes/process_base.html", "utf8");

for (const name of ["overview", "personality-results", "motivation-results",
  "cognitive-results", "team-profile", "leadership-profile", "derailment-profile"]) {
  assert.ok(code.includes('id: "' + name + '"'), "missing registered report: " + name);
}
for (const marker of ["data-report-brand-primary", "data-report-brand-logo",
  "data-report-brand-cover", "data-report-brand-company",
  "data-report-has-personality", "data-report-has-motivation", "data-report-has-cognitive",
  "data-report-has-team-profile", "data-report-has-leadership", "data-report-has-derailment"]) {
  assert.ok(workspaceHtml.includes(marker), "candidate template lacks " + marker);
}
assert.ok(context.split('"report_branding": get_report_branding(process.company)').length >= 3,
  "both live and historical candidates need their company's branding");
assert.ok(layout.includes("pdf-export-core.js") && layout.includes("candidate-report-pdf.js"),
  "both PDF scripts must load on authorized candidate pages");
assert.ok(processJs.includes('window.TalenaCandidateReportPdf?.init(sheetBody)'),
  "candidate sheet must initialize new PDF buttons on AJAX fetch");
assert.ok(!/fetch\(|XMLHttpRequest|generateAi|generateInsight/i.test(code),
  "PDF generation must not fetch data or call AI");
assert.ok(code.includes("returnBlob: Boolean(options.returnBlob)"),
  "report-packaging #360 needs the same PDF blob component");
assert.ok(code.includes('filename: "talena-" + report.id + ".pdf"'),
  "neutral filenames must not expose candidate identities");
assert.ok(code.includes("source.cloneNode(true)"),
  "PDF must use authorized current DOM snapshot");
assert.ok(code.includes("stage.remove()"), "temporary PDF stage must be removed");

function node(tag = "div", text = "") {
  return {
    tag, nodeType: 1, children: [], textContent: text,
    hidden: false,
    className: "", dataset: {}, attributes: [],
    style: { setProperty() {} },
    classList: { add() {}, remove() {} },
    setAttribute() {}, removeAttribute() {}, remove() {},
    append(...children) { this.children.push(...children); },
    querySelectorAll() { return []; },
    closest() { return null; },
    cloneNode() { return node(tag, text); }
  };
}
const pdfSpy = { calls: [], async exportSections(sections, options) {
  this.calls.push({ sections, options });
  return options.returnBlob ? new Blob(["%PDF-test"], { type: "application/pdf" }) : undefined;
} };
const documentStub = {
  documentElement: { lang: "sv" },
  createElement: tag => node(tag),
  body: { append() {} }
};
const sandbox = { window: { TalenaPdfExport: pdfSpy }, document: documentStub, Blob };
vm.runInNewContext(code, sandbox, { timeout: 1000 });
const api = sandbox.window.TalenaCandidateReportPdf;
assert.equal(api.registry.length, 7);
assert.equal(typeof api.exportReport, "function");
assert.equal(typeof api.availableReports, "function");
assert.equal(typeof api.init, "function");

function sourceFor(key) {
  const result = node("section", "Det här är ett färdigställt resultat för en syntetisk kandidat med poäng.");
  result.dataset.insightsSubpanel = key;
  result.querySelectorAll = selector => {
    if (selector.includes("p, h2")) {
      return [{ textContent: "Färdigställt resultat", hidden: false, closest: () => null }];
    }
    return [];
  };
  return result;
}
function panelFor(key, subpanels = []) {
  const result = sourceFor(key);
  result.dataset.insightsPanel = key;
  result.querySelectorAll = () => subpanels;
  return result;
}
const overview = panelFor("overview");
const personality = panelFor("personality", [sourceFor("results")]);
const motivation = panelFor("motivation", [sourceFor("results")]);
const skills = panelFor("cognitive", [sourceFor("results")]);
const reports = panelFor("reports", [
  sourceFor("team-report"), sourceFor("leadership-report"), sourceFor("derailment-report")
]);
function workspace(flags) {
  return {
    dataset: {
      reportHasPersonality: "true",
      reportHasMotivation: "true",
      reportHasCognitive: "true",
      reportHasTeamProfile: "true",
      reportHasLeadership: "true",
      reportHasDerailment: "true",
      reportBrandPrimary: "#294F72",
      reportBrandFocus: "35",
      reportBrandCompany: "Exempelföretaget",
      ...flags
    },
    querySelectorAll(selector) {
      assert.equal(selector, "[data-insights-panel]");
      return [overview, personality, motivation, skills, reports];
    }
  };
}
const good = workspace({});
assert.deepEqual(
  Array.from(api.availableReports(good), r => r.id),
  Array.from(api.registry, r => r.id)
);
const missing = workspace({
  reportHasPersonality: "false",
  reportHasTeamProfile: "false",
  reportHasLeadership: "false",
  reportHasDerailment: "false"
});
assert.deepEqual(Array.from(api.availableReports(missing).map(r => r.id)),
  ["overview", "motivation-results", "cognitive-results"],
  "must not offer report types missing completed results");

(async () => {
  const blob = await api.exportReport(good, "personality-results", { returnBlob: true });
  assert.equal(blob.type, "application/pdf");
  assert.equal(pdfSpy.calls.length, 1);
  assert.equal(pdfSpy.calls[0].options.title, "Personlighet · Resultat");
  assert.equal(pdfSpy.calls[0].options.filename, "talena-personality-results.pdf");
  assert.equal(pdfSpy.calls[0].sections.length, 2, "branded cover + report content");
  assert.equal(pdfSpy.calls[0].sections[0].cover, true);
  assert.equal(pdfSpy.calls[0].sections[1].continuous, true);
  await assert.rejects(api.exportReport(missing, "personality-results"),
    /inte tillgänglig/, "unavailable report must never become a PDF");
  assert.equal(pdfSpy.calls.length, 1, "no render call for inaccessible report");
  console.log("Candidate report PDF registry, tenant branding and safe export: OK");
})().catch(error => { console.error(error); process.exitCode = 1; });
