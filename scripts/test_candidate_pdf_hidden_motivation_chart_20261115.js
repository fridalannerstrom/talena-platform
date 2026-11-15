"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const candidate = fs.readFileSync("static/js/talena/candidate-report-export.js","utf8");
const processBase = fs.readFileSync("templates/customer/processes/process_base.html","utf8");
assert.ok(candidate.includes('await copyContent(getSource(item), id)'));
assert.ok(candidate.includes('window.TalenaPdfMotivationRose.render(source)'));
assert.ok(processBase.includes('window.TalenaPdfMotivationRose = Object.freeze({'));
assert.ok(processBase.includes('await initMotivationRoseChart(stage)'));
assert.ok(processBase.includes('chart.update("none")'));
assert.ok(processBase.includes('chart?.destroy?.()'));
assert.ok(processBase.includes('stage.remove()'));

class Node {
  constructor(name="div", text="") {
    this.tagName=name;
    this.textContent=text;
    this.children=[];
    this.parentElement=null;
    this.dataset={};
    this.attributes=[];
    this.isConnected=true;
    this.hidden=false;
    this.width=undefined;
    this.height=undefined;
    this.style={display:"",setProperty(){}};
    const classes=new Set();
    this.classList={
      add(...args){args.forEach(s=>classes.add(s));},
      remove(...args){args.forEach(s=>classes.delete(s));},
      contains(v){return classes.has(v);},
    };
  }
  set className(cls){this.classList.add(...cls.split(/\s+/).filter(Boolean));}
  setAttribute(name,value){this.attributes.push({name,value});}
  removeAttribute(name){this.attributes=this.attributes.filter(a=>a.name!==name);}
  addEventListener(){}
  matches(selector){return selector==="[data-motivation-rose-chart]"&&this.tagName==="canvas";}
  closest(){return null;}
  append(...nodes){nodes.forEach(n=>{n.parentElement=this;this.children.push(n);});}
  prepend(...nodes){nodes.forEach(n=>{n.parentElement=this;this.children.unshift(n);});}
  insertBefore(node){this.prepend(node);}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);this.parentElement=null;}
  replaceWith(node){if(this.parentElement){let p=this.parentElement;p.children[p.children.indexOf(this)]=node;node.parentElement=p;this.parentElement=null;}}
  cloneNode() {
    const copy=new Node(this.tagName,this.textContent);
    copy.width=this.width;copy.height=this.height;
    copy._motivationRoseChartInstance=undefined; // Canvas state is not cloned by DOM.
    this.children.forEach(c=>copy.append(c.cloneNode(true)));
    return copy;
  }
  querySelectorAll(selector) {
    if(selector==="*") {const found=[]; const visit=n=>n.children.forEach(c=>{found.push(c);visit(c)});visit(this);return found;}
    if(selector==="canvas")return this.querySelectorAll("*").filter(n=>n.tagName==="canvas");
    return [];
  }
  querySelector(selector) {
    if(selector==="[data-motivation-rose-chart-empty]")
      return this.querySelectorAll("*").find(n=>n.tagName==="loader")||null;
    return null;
  }
}

async function run(ready) {
  const source=new Node("section","Synthetic motivation results ".repeat(20));
  const canvas=new Node("canvas");
  canvas.width=ready?650:0;
  canvas.height=ready?650:0;
  if(ready) {
    canvas._motivationRoseChartInstance={};
    canvas.toDataURL=()=> "data:image/png;base64,live";
  }
  const loader=new Node("loader","Preparing motivation overview");
  source.append(canvas,loader);

  let workspace;
  const document={
    documentElement:{lang:"sv"},
    body:new Node("body"),
    querySelector(selector){return selector==="[data-candidate-insights-workspace]"?workspace:null;},
    createElement(tag){return new Node(tag);},
  };
  workspace=new Node("workspace");
  workspace.querySelector=selector=>selector==="#motivation-subpanel-results"?source:null;
  workspace.closest=()=>({querySelector:()=>null});

  const png="data:image/png;base64,"+"Y".repeat(140);
  let invoked=0,captured=null;
  const window={
    TalenaPdfMotivationRose:{
      async render(renderedSource){
        assert.equal(renderedSource,source,"Only the authorised current source is rendered");
        invoked++;
        return png;
      }
    },
    TalenaPdfExport:{
      async exportSections(sections,opts){
        assert.equal(opts.returnBlob,true);
        captured=sections;
        return new Blob(["pdf"],{type:"application/pdf"});
      }
    }
  };
  vm.runInNewContext(candidate,{
    document,window,Blob,
    MutationObserver:class{observe(){} disconnect(){}},
    requestAnimationFrame:cb=>cb(),
    console,URL:{}
  },{timeout:1500});

  const api=window.TalenaCandidateReports;
  api.initialize(document);
  assert.deepEqual(Array.from(api.getAvailableReports(),r=>r.id),["motivation-results"]);
  const blob=await api.exportReport("motivation-results",{returnBlob:true});
  assert.equal(blob.type,"application/pdf");
  assert.equal(invoked,ready?0:1,"Hidden charts must render offscreen; ready charts must not rerender");
  assert.equal(canvas.width,ready?650:0,"The live candidate chart must not be changed");
  const output=captured?.[1]?.node;
  assert.ok(output,"A candidate PDF body is created");
  const image=output.querySelectorAll("*").find(x=>x.tagName==="img"&&x.classList.contains("talena-candidate-pdf-chart"));
  assert.ok(image,"The exported PDF must contain the chart as a PNG");
  assert.equal(image.src,ready?"data:image/png;base64,live":png);
  assert.ok(!output.querySelectorAll("*").some(x=>x.tagName==="loader") || ready,
    "The temporary loading label must not appear in the PDF");
  assert.ok(source.querySelectorAll("canvas").includes(canvas),
    "The visible source canvas must remain intact");
  assert.ok(source.children.includes(loader),
    "The visible source loading element must remain intact");
}

(async()=>{
  await run(false);
  await run(true);
  console.log("Motivation PDF chart: hidden canvas fallback, visible chart, scoped data and no source mutation OK");
})().catch(err=>{console.error(err);process.exitCode=1;});
