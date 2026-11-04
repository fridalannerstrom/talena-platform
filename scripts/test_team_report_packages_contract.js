"use strict";
/* #449: source & anonymous-mode runtime contracts.
 * Real PDF files, large teams and user-facing UI need browser QA as well.
 */
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const read=path=>fs.readFileSync(path,"utf8");
const team=read("static/js/talena/team-report-packages.js");
const profile=read("static/js/talena/team-profile-export.js");
const combined=read("static/js/talena/team-report-export.js");
const assembler=read("static/js/talena/report-package-core.js");
const candidate=read("static/js/talena/candidate-report-packages.js");
const tpl=read("templates/customer/teams/team_detail.html");
const styles=read("static/css/talena/pages/team-report-packages.css");
const customerBase=read("templates/customer/core/layouts/customer_base.html");
for(const script of [team,profile,combined,assembler,candidate])
  assert.doesNotThrow(()=>new Function(script),"all report exporters must parse");
for(const ref of ["data-team-package-open","data-team-package-status",
    "team-report-packages.js","report-package-core.js",
    "candidate-report-packages.css","team-report-packages.css"])
  assert.ok(tpl.includes(ref),"team template missing "+ref);
assert.ok(tpl.indexOf("report-package-core.js")<tpl.indexOf("team-report-packages.js"));
assert.ok(/team-profile-export\.js' %}\?v=20261104-449-adapters-/.test(tpl) &&
  /team-report-export\.js' %}\?v=20261104-449-adapters-/.test(tpl),
  "Both existing team PDF adapters need updated cache versions so the package picker sees their new APIs");
assert.ok(team.includes('if(!adaptersReady()){status(t.unavailable,true,true);return;}'),
  "Unloaded adapters must show a clear error, never pretend the team has no reports");

assert.ok(customerBase.indexOf("report-package-core.js")<
  customerBase.indexOf("candidate-report-packages.js"));
assert.ok(styles.includes(".team-package-actions"));
assert.ok(team.includes("teamApi().exportReportForPackage()"));
assert.ok(team.includes("profileApi().exportProfileForPackage(entry.memberId)"));
assert.ok(team.includes("teamApi().exportCoverForPackage(t.package)"));
assert.ok(team.includes("pack().zipFiles(entries)")&&team.includes("pack().merge(entries"));
assert.ok(candidate.includes("core.merge(entries")&&candidate.includes("core.zipFiles(entries"),
  "Candidate and team exports should use ONE package assembler");
assert.ok(assembler.includes("PDFName.of(\"Annots\")") &&
  assembler.includes("PDFName.of(\"Fit\")") && assembler.includes("pdf.copyPages(source,source.getPageIndices())"),
  "Merged PDF must preserve pages and provide internal linked contents");
assert.ok(assembler.includes("String(i+1).padStart"),"ZIP names must preserve selected ordering");
assert.ok(assembler.includes("MAX_BYTES")&&assembler.includes("MAX_PAGES") &&
  assembler.includes("MAX_REPORTS"),"export must be bounded");
for(const tag of ["getAvailableProfiles","exportProfileForPackage",
    "beginPackage","endPackage","isAnonymous","currentPage"])
  assert.ok(profile.includes(tag),"individual profile adapter missing "+tag);
for(const tag of ["getAvailable:","exportReportForPackage",
    "exportCoverForPackage","beginPackage","endPackage"])
  assert.ok(combined.includes(tag),"composite team report adapter missing "+tag);
assert.ok(team.includes("if(!isCurrent()||isAnon())return [];"),
  "Picker must not disclose member names when anonymised");
assert.ok(team.includes('getAttribute("aria-checked")!=="false"'),
  "Missing or uninitialised anonymity switch must fail closed");
assert.ok(team.includes("if(busy)cancelled=true;") &&
  team.includes("if(cancelled||!isCurrent()||isAnon()"),
  "Once anonymity is activated during export, returning to named mode must not resume old download");
assert.ok(team.includes("if(cancelled||!adaptersReady()||!isCurrent()||isAnon()||!profileApi()?.isCurrent()"),
  "Every export step must reject cancelled, disconnected, anonymous or stale team context");
assert.ok(team.includes("MutationObserver(anonymityChanged)"),
  "Anonymous-mode changes must hide the picker");
assert.ok(team.includes("if(dialog)discard();"),
  "Anonymous toggle must immediately remove any identifying report labels");
assert.ok(profile.includes("if (!currentPage() || isAnonymous() || candidate.dataset.hasReport"),
  "Individual report export must recheck anonymous/availability during PDF creation");
assert.ok(combined.includes("if (!currentPage() || anonymousMode() !== anonymous)"),
  "Shared PDF must fail closed if anonymisation flips during rendering");
assert.ok(!/\bfetch\s*\(/.test(team),"No new private PDF fetch endpoints");
assert.ok(!/\bpostMessage\s*\(/.test(team),"No cross-origin data sharing");
assert.ok(!team.includes("console.error"),"Never log candidate-identifying export content");
assert.ok(tpl.includes("data-has-report"),"Only completed member profiles are eligible");

// Minimal anonymous-mode execution of the actual picker: verify it starts
// disabled and does not ask the profile adapter for members' names.
let anonymous=true,listener,observe,exposedNames=0;
const toggle={getAttribute:name=>name==="aria-checked"?(anonymous?"true":"false"):""};
const trigger={
  hidden:true,disabled:false,addEventListener:(name,cb)=>{if(name==="click")listener=cb;}
};
const outerStatus={textContent:"",classList:{toggle(){}}};
const page={
  isConnected:true,dataset:{teamReportName:"Private Team"},
  querySelector:selector=>selector==="[data-team-package-open]"?trigger:
    selector==="[data-team-package-status]"?outerStatus:
    selector==="#teamAnonymityToggle"?toggle:null
};
const mock={
  window:{
    TalenaTeamProfilesExport:{
      getAvailableProfiles(){exposedNames++;return [{id:"1",title:"Secret candidate"}];}
    }
  },
  document:{
    documentElement:{lang:"sv"},
    querySelector:selector=>selector.includes(".talena-team-page")?page:null
  },
  MutationObserver:class{
    constructor(callback){observe=callback}
    observe(){}
  }
};
vm.runInNewContext(team,mock,{timeout:1000});
assert.equal(trigger.hidden,false);
assert.equal(trigger.disabled,true,"Anonymised team must not permit opening report package");
assert.match(trigger.title,/anonymisering/i);
assert.equal(exposedNames,0,"No profile names can be queried when anonymous");
anonymous=false;observe();
assert.equal(trigger.disabled,false,"Picker can be enabled only after anonymisation is switched off");
assert.equal(typeof listener,"function");
anonymous=true;observe();
assert.equal(trigger.disabled,true);
assert.equal(exposedNames,0);

anonymous=false;observe();
listener();
assert.match(outerStatus.textContent,/inte läsas in/i,
  "Missing report adapters should be diagnosed, not display an empty report list");

// Simulate the same team page with a loaded composite PDF adapter and two
// authorised complete member profiles. The picker must list three reports
// without relying on another async request, and ignore an incomplete member.
class FakeElement {
  constructor(tag) {
    this.tagName=tag;this.dataset={};this.children=[];this.listeners={};
    this.classList={toggle(){}};
    this.textContent="";this.hidden=false;this.disabled=false;
  }
  append(...nodes){nodes.forEach(node=>{node.parentElement=this;this.children.push(node);});}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  setAttribute(key,value){this[key]=value;}
  addEventListener(key,fn){this.listeners[key]=fn;}
  showModal(){this.open=true;}
  close(){this.open=false;}
  remove(){}
  querySelector(selector){
    const name=selector.match(/^\[data-([a-z-]+)\]$/)?.[1];
    if(!name)return null;
    const key=name.replace(/-([a-z])/g,(_match,letter)=>letter.toUpperCase());
    const visit=element=>{
      if(Object.prototype.hasOwnProperty.call(element.dataset||{},key))return element;
      for(const child of element.children||[]){const found=visit(child);if(found)return found;}
      return null;
    };
    return visit(this);
  }
}
mock.document.body=new FakeElement("body");
mock.document.createElement=tag=>new FakeElement(tag);
mock.window.TalenaReportPackageCore={
  safeFilenamePart:value=>String(value).replace(/[^\p{L}\p{N} ]/gu,"").trim()
};
mock.window.TalenaTeamProfilesExport.getAvailableProfiles=()=>{
  exposedNames++;
  return [
    {id:"1",title:"Anna Exempel",filename:"Anna - Team.pdf"},
    {id:"2",title:"Bertil Test",filename:"Bertil - Team.pdf"}
  ];
};
mock.window.TalenaTeamProfilesExport.getMissingCount=()=>1;
mock.window.TalenaTeamReportExport={getAvailable:()=>true};
listener();
const opened=mock.document.body.children.find(child=>child.tagName==="dialog");
assert.ok(opened?.open,"Report picker must open once existing adapters are available");
const rows=opened.querySelector("[data-package-count]");
assert.equal(rows.textContent,"Valda rapporter: 3",
  "A finished team overview + 2 completed member profiles must be selectable");
const optionsList=opened.children.find(child=>child.tagName==="ol");
assert.equal(optionsList.children.length,3,"Every completed report must be rendered as a picker row");
assert.ok(optionsList.children[0].textContent!==undefined);


console.log("Team report packages #449: reuse, privacy, eligibility, PDF/ZIP and toggle OK");
