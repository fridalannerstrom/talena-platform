"use strict";
// #449: team header UX contract. Real responsive visual QA is still required.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const tpl=fs.readFileSync("templates/customer/teams/team_detail.html","utf8");
const css=fs.readFileSync("static/css/talena/pages/team-report-packages.css","utf8");
const js=fs.readFileSync("static/js/talena/team-header-actions.js","utf8");

for(const marker of [
  'class="team-page-identity"',
  'class="team-page-action-bar"',
  'class="team-actions-more" data-team-actions-more',
  'class="team-actions-more-trigger"',
  'class="team-actions-more-menu"',
  'class="team-page-action-feedback"',
  'data-team-package-open', 'id="teamAnonymityToggle"',
  'data-team-report-download','data-team-export-all',
  'data-team-report-download-status','data-team-export-status',
  "teams:team_edit","teams:team_members_edit","teams:team_delete"
])assert.ok(tpl.includes(marker),"Missing header control: "+marker);
assert.equal((tpl.match(/data-team-report-download(?:[>\s])/g)||[]).length,1,
  "The original report download button must exist exactly once");
assert.equal((tpl.match(/data-team-export-all(?:[>\s])/g)||[]).length,1,
  "The original ZIP download button must exist exactly once");
assert.ok(tpl.indexOf('class="team-page-action-feedback"')>
  tpl.indexOf('class="team-actions-more-menu"'),
  "Download feedback must remain visible outside the dropdown");
assert.ok(tpl.indexOf('data-team-export-all')<
  tpl.indexOf('class="team-page-action-feedback"'),
  "Export action stays in dropdown but feedback must not be hidden there");
assert.ok(tpl.includes("can_edit_team"),"Preserve the existing delete permission check");
assert.ok(tpl.includes("team-header-actions.js"),"Dropdown behavior must be loaded");
assert.ok(css.includes(".talena-team-page .team-page-header") &&
  css.includes("grid-template-columns:minmax(260px,1fr) auto"),
  "Give the team name room beside the condensed action row");
assert.ok(css.includes("background:rgba(255,255,255,.93)")&&
  css.includes("border-radius:18px"),
  "Team identity and actions should share a clean compact surface");
assert.ok(css.includes(".team-actions-more-menu")&&
  css.includes("position:absolute")&&css.includes("z-index:50"),
  "Dropdown must overlay content rather than push team report down");
assert.ok(css.includes("@media(max-width:1350px)")&&
  css.includes("@media(max-width:500px)"),
  "Header must adapt to tablet and phone sizes");
assert.doesNotThrow(()=>new Function(js));

// Exercise keyboard/outside-click behavior without a real browser.
let summaryFocused=0;
const summary={focus:()=>{summaryFocused++}};
const handlers={};
const details={
  open:false,dataset:{},
  querySelector:selector=>selector==="summary"?summary:null,
  addEventListener:(event,cb)=>{handlers["details:"+event]=cb;},
  contains:node=>node==="inside"||node==="item"
};
const page={
  querySelector:selector=>selector==="[data-team-actions-more]"?details:null
};
const docHandlers={};
const documentMock={
  readyState:"complete",
  querySelector:selector=>selector.startsWith(".talena-team-page")?page:null,
  addEventListener:(name,cb)=>{docHandlers[name]=cb;}
};
vm.runInNewContext(js,{document:documentMock},{timeout:1000});
assert.equal(details.dataset.menuReady,"true","Menu initializes only once");
details.open=true;
docHandlers.pointerdown({target:"outside"});
assert.equal(details.open,false,"Outside click closes the menu");
details.open=true;
let prevented=false;
docHandlers.keydown({key:"Escape",preventDefault:()=>{prevented=true}});
assert.equal(details.open,false,"Escape closes the menu");
assert.ok(prevented&&summaryFocused===1,"Escape restores keyboard focus");
details.open=true;
handlers["details:click"]({
  target:{closest:selector=>selector.includes(".team-actions-more-menu")?{disabled:false}:null}
});
assert.equal(details.open,false,"Selecting an action closes the menu");
details.open=true;
handlers["details:click"]({
  target:{closest:selector=>selector.includes(".team-actions-more-menu")
    ?{disabled:false,tagName:"BUTTON"}:null}
});
assert.equal(details.open,false,"Download action closes its menu");
assert.equal(summaryFocused,2,"Download action must restore focus to visible menu trigger");
details.open=true;
handlers["details:focusout"]({relatedTarget:"outside"});
assert.equal(details.open,false,"Leaving the menu via keyboard closes it");
assert.equal(details.dataset.menuReady,"true");
console.log("Team header UX: actions preserved, dropdown keyboard/outside behavior and responsive styles OK");
