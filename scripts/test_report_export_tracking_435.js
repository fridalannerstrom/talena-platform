/* #435: browser export metrics must be a safe, post-generation receipt. */
"use strict";
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8");
const candidate=read("static/js/talena/candidate-report-export.js");
const candPackages=read("static/js/talena/candidate-report-packages.js");
const team=read("static/js/talena/team-report-export.js");
const profiles=read("static/js/talena/team-profile-export.js");
const teamPackages=read("static/js/talena/team-report-packages.js");
const internal=read("static/js/talena/candidate-result-internal-pdf.js");
const helper=read("static/js/talena/report-export-activity.js");
const ws=read("templates/customer/processes/partials/candidate_insights/_workspace.html");
const teamHtml=read("templates/customer/teams/team_detail.html");
const preview=read("templates/candidate_results/result.html");
const backend=read("apps/activity/report_export_receipts.py");
const summary=read("apps/activity/usage_summary.py");
const check=(src,x)=>assert.ok(src.includes(x),"Missing export tracking: "+x);

for(const src of [ws,teamHtml,preview])check(src,"data-report-export-receipt-url");
check(candidate,"id !== \"manager-report\"");
check(candidate,"managerReportMetadata && !options.returnBlob");
check(candidate,"if (options.returnBlob) return blob");
check(candPackages,'\"candidate-package-\"+format');
check(team,"team-overview");
check(profiles,"team-profile");
check(profiles,"team-profiles-zip");
check(teamPackages,'\"team-package-\"+format');
check(internal,"candidate-static-report");
check(backend,"@process_view_access_required");
check(backend,"_team_visibility_queryset");
check(backend,"client_reported_generated");
check(summary,'ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED');
check(summary,'ActivityEvent.Verb.REPORT_EXPORT_GENERATED');

// No intermediate candidate PDF must be logged while a combined package is
// still being assembled. Both receipts follow download initiation.
assert.ok(candPackages.indexOf("download(output,packageFilename)") <
          candPackages.indexOf('"candidate-package-"+format'));
assert.ok(teamPackages.indexOf("download(output,filename)") <
          teamPackages.indexOf('"team-package-"+format'));
assert.ok(profiles.indexOf("saveBlob(archive, team +") <
          profiles.indexOf('"team-profiles-zip"'));
assert.ok(team.indexOf("await renderPdf({",team.indexOf('button.addEventListener("click"')) <
          team.indexOf('"team-overview"'));

async function validateHelper() {
  const calls=[];
  const uuid="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const document={cookie:"csrftoken=synthetic-token",querySelector:()=>null};
  const window={crypto:{randomUUID:()=>uuid}};
  const sandbox={window,document,
    fetch:async(url,options)=>{calls.push({url,options});return {ok:true};}};
  vm.runInNewContext(helper,sandbox,{timeout:1000});
  assert.equal(await window.TalenaReportExportActivity.record("/receipt/","team-package-zip"),true);
  assert.equal(calls.length,1);
  assert.equal(calls[0].url,"/receipt/");
  assert.equal(calls[0].options.headers["X-CSRFToken"],"synthetic-token");
  assert.equal(calls[0].options.credentials,"same-origin");
  const body=JSON.parse(calls[0].options.body);
  assert.deepEqual(Object.keys(body).sort(),["export_id","report_type"]);
  assert.equal(body.report_type,"team-package-zip");
  assert.equal(body.export_id,uuid);
  assert.equal(await window.TalenaReportExportActivity.record("/receipt/","person@example.test"),false);
  document.cookie="";
  assert.equal(await window.TalenaReportExportActivity.record("/receipt/","overview"),false);
  assert.equal(calls.length,1);
}
validateHelper().then(()=>console.log("Ticket #435 report export tracking contract OK"))
.catch(e=>{console.error(e);process.exitCode=1;});
