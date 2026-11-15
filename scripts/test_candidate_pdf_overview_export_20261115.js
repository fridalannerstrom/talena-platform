"use strict";
// Regression for Overview (#483): clickable screen cards must survive PDF
// cloning while AI interpretations and navigation are excluded.
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
const source=el("section","ai-overview-card");
const header=el("header","ai-overview-header");
const headerContent=el("div","ai-overview-header__content");
const headerDescription=el("p","","Text mentioning interpretations from the areas below.");
headerContent.append(el("h2","","Resultat i korthet"),headerDescription);
header.append(headerContent,el("div","ai-overview-header__actions"));
const grid=el("section","candidate-result-overview");
const motivation=el("button","candidate-result-overview__area candidate-result-overview__area--motivation");
motivation.append(el("span","candidate-result-overview__area-title","Motivation"));
motivation.append(el("span","candidate-result-overview__open","Visa profil"));
const motivationResults=el("span","candidate-result-overview__motivation-cards");
motivationResults.append(el("span","candidate-result-overview__motivation-card","Risk: föredrar utveckling och risktagande. ".repeat(9)));
motivation.append(motivationResults);
const ability=el("button","candidate-result-overview__area candidate-result-overview__area--skills");
ability.append(el("span","candidate-result-overview__area-title","Färdighet"));
ability.append(el("span","candidate-result-overview__open","Visa profil"));
ability.append(el("span","candidate-result-overview__skill-card","Logiskt 2 percentil"));
grid.append(motivation,ability);
const ai=el("section","talena-overview-interpretations","Sammanfattande tolkning AI-genererat ".repeat(18));
source.append(header,grid,ai);

const document={
  documentElement:{lang:"sv"},
  body:el("body"),
  createElement:tag=>el(tag),
  querySelector:selector=>selector==="[data-candidate-insights-workspace]"?workspace:null,
};
const workspace=el("div");
workspace.querySelector=selector=>selector==="#candidate-insights-panel-overview"?source:null;
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
  assert.ok(api.getAvailableReports().some(item=>item.id==="overview"));
  const pdf=await api.exportReport("overview",{returnBlob:true});
  assert.equal(pdf.type,"application/pdf");
  const cloned=bodySnapshot.querySelector(".ai-overview-card");
  assert.ok(cloned,"Overview report must be in PDF snapshot");
  assert.equal(cloned.querySelectorAll(".candidate-result-overview__area").length,2,
    "Both Motivation and Skills result cards must survive");
  assert.equal(cloned.querySelectorAll("button").length,0,
    "PDF report cards must be noninteractive");
  assert.equal(cloned.querySelectorAll(".candidate-result-overview__open").length,0,
    "No navigation buttons in printable PDF");
  assert.ok(cloned.textContent.includes("Risk: föredrar utveckling"),
    "Motivation results must stay in PDF");
  assert.ok(cloned.textContent.includes("Logiskt 2 percentil"),
    "Skills results must stay in PDF");
  assert.ok(!cloned.textContent.includes("Sammanfattande tolkning"),
    "AI interpretation must not appear in Overview PDF");
  assert.ok(!cloned.querySelector(".talena-overview-interpretations"));
  assert.ok(cloned.textContent.includes("Sammanställning av tillgängliga testresultat"));
  assert.equal(source.querySelectorAll(".candidate-result-overview__area").filter(node=>node.tagName==="button").length,2,
    "Screen cards are still interactive and must never be altered");
  assert.ok(source.querySelector(".talena-overview-interpretations"),
    "Screen AI notes remain untouched");
  assert.ok(css.includes('[data-candidate-pdf-report="overview"] .candidate-result-overview__area'));
  assert.ok(css.includes('[data-candidate-pdf-report="overview"] .candidate-result-overview__skills-list'));
  assert.ok(base.includes("20261115-overview-pdf-1"));
  assert.ok(core.includes(".candidate-result-overview__motivation-card"));
  console.log("Overview PDF: full Motivation and Skills results, no AI, source untouched, A4 styles OK");
})().catch(error=>{console.error(error);process.exitCode=1;});
