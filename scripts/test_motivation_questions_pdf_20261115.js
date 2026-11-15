"use strict";
// Motivation interview questions PDF: preserve all questions and guidance,
 // but remove interactive note fields in the export clone only.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const code=fs.readFileSync("static/js/talena/candidate-report-export.js","utf8");
const css=fs.readFileSync("static/css/talena/pages/candidate-report-export.css","utf8");
const base=fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
const core=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");

const hasClass=(element,name)=>element.classList.contains(name);
function matches(node,selector) {
  const s=selector.trim();
  if(!s)return false;
  if(s==="*")return true;
  if(s.startsWith("."))return hasClass(node,s.slice(1));
  if(s==='[data-has-result="true"]')return node.dataset.hasResult==="true";
  if(s.startsWith("["))return false;
  return s===node.tagName;
}
class FakeNode {
  constructor(tagName="div",className="",ownText="") {
    this.tagName=tagName;
    this._text=ownText;
    this.children=[];
    this.parentElement=null;
    this.isConnected=true;
    this.attributes=[];
    this.dataset={};
    this.style={display:"",setProperty(){}};
    this.hidden=false;
    const values=new Set(className.split(/\s+/).filter(Boolean));
    this.classList={
      add(...words){words.forEach(w=>values.add(w));},
      remove(...words){words.forEach(w=>values.delete(w));},
      contains(word){return values.has(word);}
    };
    Object.defineProperty(this,"className",{
      get:()=>[...values].join(" "),
      set:v=>{values.clear();String(v).split(/\s+/).filter(Boolean).forEach(w=>values.add(w));}
    });
  }
  get textContent(){return this._text+this.children.map(x=>x.textContent).join(" ");}
  set textContent(value){this._text=String(value);this.children=[];}
  get firstChild(){return this.children[0]||null;}
  append(...elements){for(const item of elements){if(item.parentElement){item.parentElement.children=item.parentElement.children.filter(x=>x!==item);}item.parentElement=this;this.children.push(item);}}
  prepend(...elements){elements.reverse().forEach(x=>{x.parentElement=this;this.children.unshift(x);});}
  insertBefore(node){this.prepend(node);}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null;}
  replaceWith(next){const parent=this.parentElement;if(parent){parent.children[parent.children.indexOf(this)]=next;next.parentElement=parent;}this.parentElement=null;}
  cloneNode(deep){
    const clone=new FakeNode(this.tagName,this.className,this._text);
    clone.attributes=this.attributes.map(a=>({...a}));
    clone.hidden=this.hidden;
    if(deep)this.children.forEach(child=>clone.append(child.cloneNode(true)));
    return clone;
  }
  setAttribute(name,value){this.attributes.push({name,value});}
  removeAttribute(name){this.attributes=this.attributes.filter(a=>a.name!==name);}
  addEventListener(){}
  closest(){return null;}
  matches(selector){return matches(this,selector);}
  querySelectorAll(selector){
    const parts=selector.split(",").map(x=>x.trim());
    const found=[];
    const visit=node=>node.children.forEach(child=>{
      if(parts.some(x=>matches(child,x)))found.push(child);
      visit(child);
    });
    visit(this);
    return found;
  }
  querySelector(selector){
    if(selector===".ai-overview-header__content p"){
      const header=this.querySelector(".ai-overview-header__content");
      return header?.querySelector("p")||null;
    }
    return this.querySelectorAll(selector)[0]||null;
  }
}

function el(tag,cls="",text=""){return new FakeNode(tag,cls,text);}
const source=el("section","candidate-insights-subpanel");
const report=el("section","motivation-questions-report");
report.dataset.hasResult="true";
report.dataset.status="completed";
const guidance=el("section","interview-section-guidance",
  "Så använder du frågorna. De AI-genererade frågorna är tänkta som inspiration och stöd inför intervjun.");
const opening=el("section","interview-static-questions");
const header=el("header","interview-static-questions__header");
header.append(el("span","interview-static-questions__icon","□"),
  el("h3","interview-static-questions__title","Inledande frågor"));
const introList=el("ol","interview-static-questions__list");
const introItem=el("li","interview-static-questions__item");
introItem.append(el("span","interview-static-questions__number","1"),
  el("span","interview-static-questions__text",
    "Hur kändes det att svara på formuläret – var det lätt eller svårt att ta ställning?"));
introList.append(introItem);
opening.append(header,introList);
report.append(guidance,opening);
const tipsHeader=el("div","personality-questions-header");
tipsHeader.append(el("div","insight-summary-kicker","AI-genererat"),
  el("h2","insight-summary-title","Tips på motivationsfrågor"));
report.append(tipsHeader);
const questions=[
  "Kan du ge exempel på situationer där du har behövt fatta beslut utan all information?",
  "Hur ser du på att arbeta i roller där du kan se hur ditt arbete bidrar till resultat?",
  "Vilka typer av arbetsmiljöer trivs du bäst i?"
];
const list=el("div","personality-question-list");
questions.forEach((question,index)=>{
  const card=el("article","personality-question-card");
  const text=el("div","personality-question-card__text",question);
  const detail=el("section","personality-question-card__detail",
    "Varför detta är viktigt: Utforska hur motivationen kommer till uttryck. "+
    "Vad du ska vara uppmärksam på i svaret: Lyssna efter konkreta exempel.");
  const note=el("div","interview-question-note",
    "Svar / anteckningar. Obs: Skriv inte kandidatens namn. "+
    "Skriv din anteckning och klicka på Spara.");
  note.dataset.interviewQuestionNoteField="";
  note.append(el("textarea","","privat anteckning som aldrig ska exporteras"));
  card.append(text,detail,note);
  list.append(card);
});
report.append(list,el("div","purpose-fit-disclaimer",
  "Motivationsresultat visar möjliga källor till energi och preferenser."));
source.append(report);

const document={
  documentElement:{lang:"sv"},
  body:el("body"),
  createElement:tag=>el(tag),
  querySelector:selector=>selector==="[data-candidate-insights-workspace]"?workspace:null,
};
const workspace=el("div");
workspace.querySelector=selector=>selector==="#motivation-subpanel-questions"?source:null;
workspace.closest=()=>null;
let bodySnapshot=null;
const window={
  TalenaPdfExport:{
    exportSections:async(sections,options)=>{
      assert.equal(options.returnBlob,true);
      bodySnapshot=sections[1].node;
      return new Blob(["synthetic PDF"],{type:"application/pdf"});
    }
  }
};
vm.runInNewContext(code,{document,window,Blob,
  MutationObserver:class{observe(){}disconnect(){}},
  requestAnimationFrame:callback=>callback(),console,URL:{}},{timeout:1500});

(async()=>{
  const api=window.TalenaCandidateReports;
  api.initialize(document);
  assert.ok(api.getAvailableReports().some(item=>item.id==="motivation-questions"));
  const pdf=await api.exportReport("motivation-questions",{returnBlob:true});
  assert.equal(pdf.type,"application/pdf");
  const clone=bodySnapshot.querySelector(".motivation-questions-report");
  assert.ok(clone,"Motivation interview questions must be exported");
  assert.equal(clone.querySelectorAll(".personality-question-card").length,3,
    "Every generated question and its explanations must remain");
  for(const question of questions)assert.ok(clone.textContent.includes(question));
  assert.ok(clone.textContent.includes("Varför detta är viktigt"));
  assert.ok(clone.textContent.includes("Vad du ska vara uppmärksam på i svaret"));
  assert.equal(clone.querySelectorAll(".interview-question-note").length,0,
    "Interactive note editor and all its hints must not appear in the PDF");
  assert.ok(!clone.textContent.includes("Svar / anteckningar"));
  assert.ok(!clone.textContent.includes("Skriv din anteckning"));
  assert.ok(!clone.textContent.includes("privat anteckning"));
  assert.equal(clone.querySelectorAll(".interview-static-questions").length,1,
    "The printed opening-questions card must be retained");
  assert.ok(clone.textContent.includes("Inledande frågor"));
  assert.ok(clone.textContent.includes("Hur kändes det"));
  assert.ok(clone.textContent.includes("Så använder du frågorna"));
  assert.ok(clone.textContent.includes("Motivationsresultat visar möjliga"));
  assert.equal(clone.querySelectorAll(".insight-summary-kicker").length,0,
    "Decorative AI-status eyebrows are screen-only");
  assert.equal(source.querySelectorAll(".interview-question-note").length,3,
    "The original editable candidate screen must remain untouched");

  const scope='[data-candidate-pdf-report="motivation-questions"]';
  assert.ok(css.includes(scope+" .talena-candidate-pdf-body.candidate-insight-page {"));
  assert.ok(css.includes(scope+" .interview-static-questions__header {"));
  assert.ok(css.includes(scope+" .interview-static-questions__item {"));
  assert.ok(css.includes(scope+" .interview-static-questions__number {"));
  assert.ok(css.includes('list-style:none !important;'),"Do not print duplicate ordered-list numbers");
  assert.ok(base.includes("20261115-cognitive-results-pagination-1"),
    "PDF scripts and styles need fresh cache versions");
  assert.ok(core.includes("getMotivationQuestionsPageGuides"),
    "PDF pagination must protect complete question cards");
  // Typography and whitespace must be scoped to the PDF export clone.
  const pdfRule = (selector) => {
    const start=css.indexOf(scope+" "+selector+" {");
    assert.ok(start >= 0,"Missing Motivation PDF style for "+selector);
    return css.slice(start,css.indexOf("}",start));
  };
  assert.ok(pdfRule(".personality-question-card__text").includes("font-size:17px !important;"),
    "Interview question font needs to be noticeably larger");
  assert.ok(pdfRule(".personality-question-list").includes("gap:18px !important;"),
    "Add breathing room between question cards");
  assert.ok(pdfRule(".personality-question-card__header").includes("margin-bottom:16px !important;"),
    "Separate the question from its guidance panels");
  assert.ok(pdfRule(".personality-question-card__detail").includes("padding:14px 15px !important;"),
    "Give explanatory panels more interior whitespace");
  console.log("Motivation interview PDF: all questions and intro preserved, UI notes removed, opening card styled, on-screen unchanged");
})().catch(error=>{console.error(error);process.exitCode=1;});
