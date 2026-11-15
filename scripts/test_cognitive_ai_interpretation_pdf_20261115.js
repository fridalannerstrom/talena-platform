"use strict";
// Regression for Cognitive AI interpretation PDF: remove only the small
// screen provenance tags and outer border, without deleting the AI content.
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
const report=el("div","cognitive-ai-report");
report.dataset.hasResult="true";
report.dataset.status="completed";
const kicker=el("div","insight-summary-kicker","AI-genererad insikt");
const header=el("h2","insight-summary-title","Färdighetstolkning");
const context=el("div","personality-questions-context-note",
  "Om AI-tolkningen. Du ansvarar för att granska tolkningen och bedöma vad som är relevant.");
report.append(kicker,header,context);
const headings=[
  ["Praktisk tolkning","Personens färdighetsresultat kan visa behov av stöd i komplexa uppgifter."],
  ["Relevanta överväganden","Tydliga instruktioner och anpassat stöd kan vara relevant."]
];
headings.forEach(([title,content])=>{
  const section=el("section","purpose-fit-section");
  const titleRow=el("div","talena-ai-title-row");
  titleRow.append(el("h3","purpose-fit-section-title",title),
    el("span","talena-ai-generated-badge","✦ AI-genererat"));
  section.append(titleRow,el("p","purpose-fit-summary",content));
  report.append(section);
});
report.append(el("div","talena-ai-field-badge","AI-genererat"));
report.append(el("div","insight-summary-kicker","AI-generated insight"));
source.append(report);

const document={
  documentElement:{lang:"sv"},
  body:el("body"),
  createElement:tag=>el(tag),
  querySelector:selector=>selector==="[data-candidate-insights-workspace]"?workspace:null,
};
const workspace=el("div");
workspace.querySelector=selector=>selector==="#cognitive-subpanel-interpretation"?source:null;
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
  assert.ok(api.getAvailableReports().some(item=>item.id==="cognitive-interpretation"));
  const pdf=await api.exportReport("cognitive-interpretation",{returnBlob:true});
  assert.equal(pdf.type,"application/pdf");
  const clone=bodySnapshot.querySelector(".cognitive-ai-report");
  assert.ok(clone,"Cognitive interpretation content must be in the PDF");
  assert.equal(clone.querySelectorAll(".talena-ai-generated-badge").length,0,
    "All injected AI-generated badges must be absent from the PDF");
  assert.equal(clone.querySelectorAll(".talena-ai-field-badge").length,0,
    "Legacy AI badges must also be removed");
  assert.equal(clone.querySelectorAll(".insight-summary-kicker").length,0,
    "Legacy Swedish/English AI eyebrow labels must be removed");
  assert.equal(clone.querySelectorAll(".purpose-fit-section").length,2,
    "No interpretation sections should disappear");
  assert.ok(clone.textContent.includes("Om AI-tolkningen"),
    "Keep the AI-methodology and reviewer-responsibility information");
  assert.ok(clone.textContent.includes("Färdighetstolkning"),"Keep PDF title");
  assert.ok(!clone.textContent.includes("✦ AI-genererat"),"No injected AI status labels");
  for(const [heading,copy] of headings) {
    assert.ok(clone.textContent.includes(heading),"Keep section heading "+heading);
    assert.ok(clone.textContent.includes(copy),"Keep interpreted content "+heading);
  }
  assert.equal(source.querySelectorAll(".talena-ai-generated-badge").length,2,
    "All original on-screen AI provenance badges must remain");
  assert.equal(source.querySelectorAll(".insight-summary-kicker").length,2,
    "The original on-screen eyebrow labels remain untouched");
  assert.ok(css.includes(
    '[data-candidate-pdf-report="cognitive-interpretation"] .talena-candidate-pdf-body.candidate-insight-page {'
  ),"Only the Cognitive interpretation PDF frame is targeted");
  const scope='[data-candidate-pdf-report="cognitive-interpretation"] .talena-candidate-pdf-body.candidate-insight-page {';
  const at=css.indexOf(scope);
  assert.ok(at>=0,"PDF-only layout scope must exist");
  const block=css.slice(at,css.indexOf("}",at));
  assert.ok(block.includes("border:0 !important;") &&
    block.includes("padding:0 !important;") &&
    block.includes("box-shadow:none !important;"),
    "Outer border, inset and shadow must be removed");
  assert.ok(base.includes("20261115-personality-description-pages-1"),
    "CSS and JS assets need a new version to bypass cached files");
  console.log("Cognitive interpretation PDF: tags gone, outer border gone, full AI content and on-screen badges unchanged");
})().catch(error=>{console.error(error);process.exitCode=1;});
