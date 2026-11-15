"use strict";
// Synthetic A4 PDF pagination: a question, its purpose and listening guidance
// must never be divided at the page edge. The live UI is unaffected.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const js=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");

function box(top,bottom){return {getBoundingClientRect:()=>({
  top,bottom,height:bottom-top,width:900
})};}
const guidance=box(50,270), opening=box(300,485);
const heading=box(535,660), footer=box(2215,2320);
const cards=[box(665,990),box(1015,1370),box(1395,1780),box(1805,2190)];
const protectedBlocks=[
  [50,270],[300,485],[535,990],
  [665,990],[1015,1370],[1395,1780],[1805,2190],[2215,2320]
];
const node={
  closest(selector){return selector==='[data-candidate-pdf-report="motivation-questions"]'?{}:null;},
  getBoundingClientRect(){return {top:0,bottom:2400,width:900,height:2400};},
  querySelectorAll(selector){
    if(selector==="img")return [];
    if(selector.includes(".interview-section-guidance"))return [guidance,opening,...cards,footer];
    return [];
  },
  querySelector(selector){
    if(selector===".personality-questions-header")return heading;
    if(selector===".personality-question-card")return cards[0];
    return null;
  }
};
const pages=[];
const document={
  fonts:{ready:Promise.resolve()},
  documentElement:{clientWidth:1200},
  createElement(tag){
    assert.equal(tag,"canvas");
    return {
      width:0,height:0,
      getContext(){return {drawImage(_src,_x,y,_width,h){pages.push({start:y,height:h});}};},
      toDataURL(){return "data:image/jpeg;base64,fixture";}
    };
  }
};
const window={
  html2canvas:async()=>({width:900,height:2400}),
  jspdf:{jsPDF:class{
    constructor(){this.internal={pageSize:{getWidth:()=>210,getHeight:()=>297}};}
    setProperties(){} addPage(){} addImage(){} setFont(){}
    setFontSize(){}setTextColor(){}text(){}
    output(){return new ArrayBuffer(12);}
  }}
};
vm.runInNewContext(js,{document,window,Blob},{timeout:1500});

(async()=>{
  const pdf=await window.TalenaPdfExport.exportSections(
    [{node,continuous:true}],{title:"Motivation interview guide",returnBlob:true}
  );
  assert.equal(pdf.type,"application/pdf");
  assert.ok(pages.length>=2&&pages.length<=3,
    "The question guide should fit within a few well-filled A4 pages");
  assert.equal(pages[0].start,0);
  for(let i=0;i<pages.length;i++){
    const page=pages[i];
    if(i)assert.equal(page.start,pages[i-1].start+pages[i-1].height);
    if(i===pages.length-1)continue;
    const boundary=page.start+page.height;
    const split=protectedBlocks.filter(([from,to])=>boundary>from&&boundary<to);
    assert.deepEqual(split,[],"Page boundary must not cut a question or guidance block");
  }
  assert.equal(pages.at(-1).start+pages.at(-1).height,2400);
  const old=window.TalenaPdfExport.calculatePageSlices(2250,1000,[760,1780]);
  assert.equal(old[0].height,760,
    "Other reports must retain original page-break behaviour");
  console.log("Motivation interview PDF: entire opening card, question blocks, heading and disclaimer remain uncut");
})().catch(e=>{console.error(e);process.exitCode=1;});
