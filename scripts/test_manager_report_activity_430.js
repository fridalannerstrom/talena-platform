/* #430: technical contract for Chefsrapport activity across both UIs and exports. */
"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const read = file => fs.readFileSync(file, "utf8");
const customer = read("static/js/talena/after-interview-tabs.js");
const packageExport = read("static/js/talena/candidate-report-export.js");
const metadata = read("static/js/talena/manager-report-pdf-metadata.js");
const history = read("static/js/talena/manager-report-activity.js");
const backend = read("apps/processes/manager_report_pdf.py");
const historyApi = read("apps/processes/manager_report_activity.py");
const adminOne = read("templates/admin/accounts/customer/candidate_detail.html");
const adminTwo = read("templates/admin/accounts/companies/company_candidate_sheet.html");
const adminExplorer = read("apps/activity/admin_views.py");

for (const token of [
  "talena:manager-report-activity-changed",
  'window.TalenaManagerReportPdf.recordGenerated(outputRoot, reportMetadata)',
  "managerReportCard.appendChild(managerReportAudit)",
]) assert.ok(customer.includes(token), "missing customer audit UI: " + token);

for (const token of [
  "await window.TalenaManagerReportPdf.prepare(workspace)",
  "await window.TalenaManagerReportPdf.recordGenerated(workspace, managerReportMetadata)",
]) assert.ok(packageExport.includes(token), "missing package audit: " + token);

assert.ok(metadata.includes(".talena-report-audit"));
assert.ok(metadata.includes("prepared_event_id"));
assert.ok(metadata.includes("recordGenerated"));
assert.ok(!metadata.includes("PDF downloaded"));
assert.ok(history.includes("talena-report-audit__details"));
assert.ok(history.includes("talena-report-audit__summary"));
assert.ok(history.includes("Europe/Stockholm"));
assert.ok(history.includes("textContent = content"));
assert.ok(history.includes("talena:manager-report-activity-changed"));

assert.ok(backend.includes("MANAGER_REPORT_PDF_GENERATED"));
assert.ok(backend.includes("select_for_update()"));
assert.ok(backend.includes("actor=request.user"));
assert.ok(backend.includes("client_reported_generated"));
assert.ok(historyApi.includes("can_view_platform_audit(request.user)"));
assert.ok(historyApi.includes("process_view_access_required"));
assert.ok(!historyApi.includes('"text":'));
assert.ok(adminOne.includes("process_candidate_manager_report_activity_admin"));
assert.ok(adminTwo.includes("process_candidate_manager_report_activity_admin"));
assert.ok(adminExplorer.includes('"reports": {"manager_report_pdf_prepared", "manager_report_pdf_generated"}'));

const directIndex = customer.indexOf("await renderElementAsPdf(printableReport, filename, outputRoot);");
const directRecord = customer.indexOf("await window.TalenaManagerReportPdf.recordGenerated(outputRoot, reportMetadata);");
assert.ok(directIndex > 0 && directRecord > directIndex, "record generation only after PDF success");
const blobIndex = packageExport.indexOf("const blob = await window.TalenaPdfExport.exportSections(", packageExport.indexOf("async function exportReport"));
const packageRecord = packageExport.indexOf("await window.TalenaManagerReportPdf.recordGenerated(workspace, managerReportMetadata)");
assert.ok(blobIndex > 0 && packageRecord > blobIndex, "record package generation after blob success");
console.log("Ticket #430 report activity contract OK");
