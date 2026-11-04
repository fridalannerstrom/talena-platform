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
const sandbox={
  document:{documentElement:{lang:"sv"},querySelector:()=>null},
  window:{}
};
vm.runInNewContext(js,sandbox,{timeout:1000});
assert.equal(typeof sandbox.window.TalenaReportPackages.initialize,"function");
console.log("Report package contracts: scoped export, PDF/ZIP, order, TOC links, limits OK");