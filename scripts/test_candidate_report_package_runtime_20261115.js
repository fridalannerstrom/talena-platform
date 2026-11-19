"use strict";
// Synthetic browser regression: package exports only the three assessment
// results, excludes AI and other reports in both formats, and attributes
// failures to the correct result PDF rather than the PDF/ZIP assembler.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");

const source=fs.readFileSync("static/js/talena/candidate-report-packages.js","utf8");
class Element {
  constructor(tag) {
    this.tagName=tag.toLowerCase();
    this.children=[];this.parentElement=null;this.dataset={};
    this.attrs={};this.events={};this.style={};this.isConnected=true;
    this.hidden=false;this.disabled=false;this.checked=false;this.value="";
    this._textContent="";
    const classes=new Set();
    this.classList={
      add:(...values)=>values.forEach(value=>classes.add(value)),
      remove:(...values)=>values.forEach(value=>classes.delete(value)),
      toggle:(value,force)=>{const enable=force===undefined?!classes.has(value):force;enable?classes.add(value):classes.delete(value);return enable;},
      contains:value=>classes.has(value),
    };
  }
  set className(value){this.classList.add(...String(value).split(/\s+/).filter(Boolean));}
  get className(){return "";}
  set textContent(value){this._textContent=String(value);}
  get textContent(){return this._textContent;}
  setAttribute(key,value){this.attrs[key]=value;}
  getAttribute(key){return Object.hasOwn(this.attrs,key)?this.attrs[key]:null;}
  addEventListener(type,callback){(this.events[type]||=[]).push(callback);}
  async trigger(type) {
    const results=(this.events[type]||[]).map(fn=>fn({preventDefault(){},dataTransfer:{}}));
    await Promise.all(results.map(Promise.resolve.bind(Promise)));
  }
  append(...children){for(const child of children){this.children.push(child);child.parentElement=this;}}
  appendChild(child){this.append(child);}
  replaceChildren(...children){this.children=[];this.append(...children);}
  remove(){if(this.parentElement){this.parentElement.children=this.parentElement.children.filter(c=>c!==this);this.parentElement=null;}}
  showModal(){this.open=true;}
  close(){this.open=false;}
  focus(){}
  querySelectorAll(selector) {
    const result=[];
    const visit=node=>{
      for(const child of node.children){
        const matches=selector==="button,input" ? ["button","input"].includes(child.tagName)
          : selector===".talena-package-row" ? child.classList.contains("talena-package-row")
          : false;
        if(matches)result.push(child);
        visit(child);
      }
    };
    visit(this);
    return result;
  }
  querySelector(selector) {
    let match;
    const visit=node=>{
      if(match)return;
      for(const child of node.children) {
        if(match)return;
        const target=selector.match(/^\[data-([a-z-]+)\]$/)?.[1];
        const key=target?.replace(/-([a-z])/g,(_,letter)=>letter.toUpperCase());
        if(key&&Object.hasOwn(child.dataset,key))match=child;
        else if(selector==='input[name="talena-package-mode"]:checked'&&
          child.tagName==="input"&&child.name==="talena-package-mode"&&child.checked)match=child;
        if(!match)visit(child);
      }
    };
    visit(this);
    return match||null;
  }
}

async function run(format,failIndex,assembleFails=false){
  let made=[], downloaded=0, assembled=0;
  const reports=[
    {id:"overview",title:"Överblick",filename:"overview.pdf"},
    {id:"personality-results",title:"Personlighet · Resultat",filename:"personality.pdf"},
    {id:"motivation-interpretation",title:"Motivation · AI-tolkning",filename:"ai.pdf"},
    {id:"motivation-results",title:"Motivation · Resultat",filename:"motivation.pdf"},
    {id:"cognitive-results",title:"Färdighet · Resultat",filename:"cognitive.pdf"},
    {id:"manager-report",title:"Chefsrapport",filename:"manager.pdf"},
  ];
  const body=new Element("body");
  const header=new Element("div");
  const sheet={querySelector:()=>header};
  const workspace={
    isConnected:true,
    closest:()=>sheet,
    querySelector:()=>null,
    dataset:{},
  };
  const document={
    documentElement:{lang:"sv"},
    body,
    createElement(tag){return new Element(tag);},
    querySelector(selector){
      return selector==="[data-candidate-insights-workspace]"?workspace:null;
    }
  };
  const api={
    getAvailableReports:()=>reports,
    getPackageFilename:()=>format==="pdf"?"test.pdf":"test.zip",
    async exportReport(id,options){
      assert.equal(options.returnBlob,true);
      made.push(id);
      if(id===failIndex)throw Error("Do not expose private candidate data");
      return new Blob(["%PDF-1.7"],{type:"application/pdf"});
    },
    async exportCover(){return new Blob(["%PDF"],{type:"application/pdf"});}
  };
  const pack={
    async ensure(){},
    async zipFiles(entries){assembled++;assert.equal(entries.length,3);if(assembleFails)throw Error("zip failure");return new Blob(["zip"],{type:"application/zip"});},
    async merge(entries){assembled++;assert.equal(entries.length,3);if(assembleFails)throw Error("pdf failure");return new Blob(["pdf"],{type:"application/pdf"});},
    download(){downloaded++;}
  };
  const logs=[];
  const window={TalenaCandidateReports:api,TalenaReportPackageCore:pack,
    console:{warn:(...args)=>logs.push(args)},
  };
  const context={document,window,console:window.console,
    requestAnimationFrame:callback=>{Promise.resolve().then(callback);}};
  vm.runInNewContext(source,context,{timeout:1000});
  const trigger=header.children.find(x=>x.getAttribute("data-candidate-report-package-open")!==null);
  assert.ok(trigger,"Open report package button should render");
  await trigger.trigger("click");
  const dialog=body.children.find(x=>x.tagName==="dialog");
  assert.ok(dialog?.open);
  const options=dialog.querySelectorAll("button,input");
  const modes=options.filter(x=>x.name==="talena-package-mode");
  assert.equal(modes.length,2);
  modes.forEach(x=>x.checked=x.value===format);
  const download=dialog.querySelector("[data-package-download]");
  assert.ok(download);
  await download.trigger("click");
  const status=dialog.querySelector("[data-package-status]").textContent;
  const rows=dialog.querySelectorAll(".talena-package-row");
  return {status,made,downloaded,assembled,rows,logs};
}

(async()=>{
  for(const format of ["pdf","zip"]){
    const failed=await run(format,"motivation-results");
    assert.deepEqual(failed.made,["personality-results","motivation-results"]);
    assert.equal(failed.downloaded,0);
    assert.equal(failed.assembled,0,"Do not assemble an incomplete package");
    assert.match(failed.status,/Motivation · Resultat/);
    assert.match(failed.status,/ladda ner rapporten separat/);
    assert.ok(!failed.status.includes("private candidate"));
    assert.equal(failed.rows.length,3,"Only the three result PDFs should be selectable");
    assert.ok(failed.rows[1].classList.contains("is-failed"));
    assert.ok(!failed.rows[0].classList.contains("is-failed"));
    assert.equal(failed.logs[0]?.[1]?.reportId,"motivation-results");

    const success=await run(format,null);
    assert.deepEqual(success.made,[
      "personality-results","motivation-results","cognitive-results"
    ],"Never export overview, AI interpretations, manager report or other types");
    assert.equal(success.assembled,1);
    assert.equal(success.downloaded,1);
    assert.match(success.status,/Nedladdningen har startat/);

    const assembly=await run(format,null,true);
    assert.equal(assembly.assembled,1);
    assert.equal(assembly.downloaded,0);
    assert.match(assembly.status,/paketet kunde inte sättas ihop/);
    assert.ok(assembly.rows.every(row=>!row.classList.contains("is-failed")));
  }
  console.log("Candidate report package runtime: results only, PDF+ZIP, individual failure and assembly failure OK");
})().catch(error=>{console.error(error);process.exitCode=1;});
