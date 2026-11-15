"use strict";
// The browser's quick scale relies on :has([data-score]), but the exported
// PDF clone strips data-* attributes. Assert the path is still visible from
// the centre (5/6) to every possible selected STEN score (1..10).
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
  getAttribute(name){return this.attributes.find(a=>a.name===name)?.value??null;}
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
const source=el("section","candidate-insights-subpanel","Personlighet karaktärsdragsprofil 18 resultat. ".repeat(5));
const quick=el("section","personality-quick-view");
for(let selected=1;selected<=10;selected++) {
  const scale=el("div","personality-quick-scale");
  for(let score=1;score<=10;score++) {
    const segment=el("span","personality-quick-scale__segment"+(score===selected?" personality-quick-scale__segment--selected":""));
    segment.setAttribute("data-score",String(score));
    scale.append(segment);
  }
  quick.append(scale);
}
const invalid=el("div","personality-quick-scale");
const empty=el("span","personality-quick-scale__segment");
empty.setAttribute("data-score","invalid");
invalid.append(empty);
quick.append(invalid);
const indicator=el("div","personality-indicator-scale");
indicator.append(el("span","personality-indicator-scale__segment personality-indicator-scale__segment--selected"));
source.append(quick,indicator);
const document={
  documentElement:{lang:"sv"},
  body:el("body"),
  createElement:tag=>el(tag),
  querySelector:selector=>selector==="[data-candidate-insights-workspace]"?workspace:null,
};
const workspace=el("div");
workspace.querySelector=selector=>selector==="#personality-subpanel-results"?source:null;
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
  assert.ok(api.getAvailableReports().some(item=>item.id==="personality-results"));
  const pdf=await api.exportReport("personality-results",{returnBlob:true});
  assert.equal(pdf.type,"application/pdf");
  const report=bodySnapshot.querySelector(".personality-quick-view");
  assert.ok(report,"The PDF keeps the original quick profile");
  const scales=report.querySelectorAll(".personality-quick-scale");
  assert.equal(scales.length,11);
  const originalScales=source.querySelectorAll(".personality-quick-scale");
  for(let selected=1;selected<=10;selected++) {
    const segments=scales[selected-1].querySelectorAll(".personality-quick-scale__segment");
    assert.equal(segments.length,10);
    const selectedFlags=[],pathFlags=[];
    segments.forEach((segment,index)=>{
      const score=index+1;
      if(segment.classList.contains("talena-personality-pdf-selected"))selectedFlags.push(score);
      if(segment.classList.contains("talena-personality-pdf-path"))pathFlags.push(score);
      assert.equal(segment.getAttribute("data-score"),null,
        "PDF data-score attributes are removed AFTER the printable path is marked");
    });
    const expected=selected<=5
      ? Array.from({length:6-selected},(_,i)=>selected+i)
      : Array.from({length:selected-5},(_,i)=>i+6);
    assert.deepEqual(pathFlags,expected,
      "The path must extend contiguously from the midpoint to selected "+selected);
    assert.deepEqual(selectedFlags,[selected],"The selected score stays darkest");
    const onScreen=originalScales[selected-1].querySelectorAll(".personality-quick-scale__segment");
    assert.ok(onScreen.every(el=>!el.classList.contains("talena-personality-pdf-path")),
      "Do not change the live personality chart");
    assert.equal(onScreen[selected-1].getAttribute("data-score"),String(selected),
      "The live scale keeps its source data attributes");
  }
  assert.ok(!scales[10].querySelector(".talena-personality-pdf-path"),
    "Malformed/unselected scales should remain neutral");
  assert.ok(!bodySnapshot.querySelector(".personality-indicator-scale")
    .querySelector(".talena-personality-pdf-path"),
    "The detailed indicator scale must be untouched");

  const scope='[data-candidate-pdf-report="personality-results"]';
  assert.ok(css.includes(".personality-quick-view .personality-quick-scale__segment.talena-personality-pdf-path {"),
    "PDF stylesheet includes continuous midpoint path");
  assert.ok(css.includes(".personality-quick-view .personality-quick-scale__segment.talena-personality-pdf-selected {"),
    "PDF stylesheet distinguishes selected value from connecting path");
  assert.ok(base.includes("20261115-personality-description-pages-1"),
    "PDF asset cache version updated");
  console.log("Personality quick PDF: all 10 midpoint-to-result paths, preserved live chart, no data attribute dependency");
})().catch(error=>{console.error(error);process.exitCode=1;});
