"use strict";
// Regression for the user's 3-page Färdighet · Resultat PDF:
// percentile levels must never be split between physical A4 pages.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const js=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");
const css=fs.readFileSync("static/css/talena/pages/candidate-report-export.css","utf8");
const layout=fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
assert.match(layout,/candidate-report-export\.css' %}\?v=[a-zA-Z0-9_-]+/,"The PDF stylesheet must use a versioned asset URL");
const scope='[data-candidate-pdf-report="cognitive-results"]';
assert.ok(css.includes(scope+' .talena-candidate-pdf-body.candidate-insight-page {'));
assert.ok(css.includes(scope+' .candidate-insights-subpanel .purpose-fit-card {'));
assert.ok(css.includes(scope+' .cognitive-percentile-guide__level,'));
assert.ok(css.includes('padding:0 !important;'),
  "Extra screen inset is removed only from this report's PDF");
assert.ok(css.includes(scope+' .cognitive-percentile-guide__summary-hint {'),
  "Expandable interactive controls must not appear in a static PDF");

const box=(top,bottom)=>({
  getBoundingClientRect(){return {top,bottom,height:bottom-top,width:900};}
});
const cards=[box(100,720),box(100,720),box(100,720)];
const summary=box(810,900);
const intro=box(922,1030);
const levels=[
  box(1065,1205),
  box(1240,1505),
  box(1530,1750),
  box(1780,2180)
];
const footnote=box(2220,2300);
const protectedBlocks=[
  [100,720],[810,1205],[922,1030],
  [1065,1205],[1240,1505],[1530,1750],
  [1780,2180],[2220,2300]
];
const node={
  closest(selector){
    return selector==='[data-candidate-pdf-report="cognitive-results"]'?{}:null;
  },
  getBoundingClientRect(){return {top:0,bottom:2360,width:900,height:2360};},
  querySelectorAll(selector){
    if(selector==="img")return [];
    if(selector===".cognitive-result-card")return cards;
    if(selector===".cognitive-percentile-guide__level")return levels;
    if(selector===".cognitive-percentile-guide__intro, .cognitive-percentile-guide + .small")
      return [intro,footnote];
    return [];
  },
  querySelector(selector){
    if(selector===".cognitive-percentile-guide > summary")return summary;
    if(selector===".cognitive-percentile-guide__level")return levels[0];
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
  html2canvas:async()=>({width:900,height:2360}),
  jspdf:{jsPDF:class{
    constructor(){this.internal={pageSize:{getWidth:()=>210,getHeight:()=>297}};}
    setProperties(){}addPage(){}addImage(){}setFont(){}
    setFontSize(){}setTextColor(){}text(){}
    output(){return new ArrayBuffer(12);}
  }}
};
vm.runInNewContext(js,{document,window,Blob},{timeout:1500});
(async()=>{
  const pdf=await window.TalenaPdfExport.exportSections(
    [{node,continuous:true}],
    {title:"Synthetic cognitive percentile report",returnBlob:true}
  );
  assert.equal(pdf.type,"application/pdf");
  assert.equal(pages.length,2,
    "The complete guide should fit two well-balanced content pages");
  assert.equal(pages[0].start,0);
  assert.equal(pages.at(-1).start+pages.at(-1).height,2360);
  for(let i=0;i<pages.length-1;i++){
    const cut=pages[i].start+pages[i].height;
    const split=protectedBlocks.filter(([start,end])=>cut>start&&cut<end);
    assert.deepEqual(split,[],
      "Never cut a score card or a percentile level's title, meaning and list");
  }
  const firstCut=pages[0].start+pages[0].height;
  assert.equal(firstCut,1240,
    "If page 1 would cut the 20–40 level, break immediately before the level");
  const regular=window.TalenaPdfExport.calculatePageSlices(2250,1000,[760,1780]);
  assert.equal(regular[0].height,760,
    "Do not change pagination of other PDF reports");
  console.log("Cognitive result PDF: score cards and four percentile levels uncut; outer frame and extra inset removed");
})().catch(error=>{console.error(error);process.exitCode=1;});
