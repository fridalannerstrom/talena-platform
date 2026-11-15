"use strict";
// The short character-trait PDF uses a different layout from the detailed
// indicator profile. The 3 profile categories should not be orphaned.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const src=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");
const css=fs.readFileSync("static/css/talena/pages/candidate-report-export.css","utf8");
const layout=fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
assert.ok(layout.includes("20261115-personality-questions-parity-1"));
const scope='[data-candidate-pdf-report="personality-results"] .personality-quick-view';
assert.ok(css.includes(scope+" .personality-quick-section {"));
assert.ok(css.includes(scope+" .personality-quick-row__pole p {"));
assert.ok(css.includes("font-size:11px !important;"));
assert.ok(src.includes("getPersonalityQuickPageGuides"));
assert.ok(src.includes("getPersonalityResultsPageGuides"),
  "Detailed personality pagination must continue to be supported");

function box(top,bottom){return {getBoundingClientRect:()=>({
  top,bottom,height:bottom-top,width:900
})};}
const overview=box(145,650);
function section(from,to){
  const header=box(from,from+45);
  const rows=Array.from({length:6},(_,i)=>box(from+50+i*((to-from-55)/6),from+50+(i+1)*((to-from-55)/6)-3));
  return {
    from,to,header,rows,
    getBoundingClientRect(){return box(from,to).getBoundingClientRect();},
    querySelector(sel) {
      if(sel===".personality-quick-section__header")return header;
      if(sel===".personality-quick-row")return rows[0];
      return null;
    },
    querySelectorAll(sel){return sel===".personality-quick-row"?rows:[];}
  };
}
// Synthetic layout mimics page 2: at-a-glance summary + full first
// category, while the second category heading is close to the A4 edge.
const groups=[section(685,1175),section(1200,1720),section(1750,2270)];
const quick={
  querySelector(sel){return sel===".personality-overview-chart"?overview:null;},
  querySelectorAll(sel){return sel===".personality-quick-section"?groups:[];}
};
const root={
  closest(sel){return sel==='[data-candidate-pdf-report="personality-results"]'?{}:null;},
  getBoundingClientRect(){return {top:0,bottom:2300,height:2300,width:900};},
  querySelector(sel){return sel===".personality-quick-view"?quick:null;},
  querySelectorAll(sel){
    if(sel==="img")return [];
    // Natural breaks on each row; the quick-guide ranges add protection
    // for each complete category and heading+first-row.
    if(sel.includes(".personality-quick-row"))
      return groups.flatMap(group=>group.rows);
    return [];
  }
};
const pageImages=[];
const document={
  documentElement:{clientWidth:1200},
  fonts:{ready:Promise.resolve()},
  createElement(tag){
    assert.equal(tag,"canvas");
    return {
      width:0,height:0,
      getContext(){return {drawImage(_src,_x,y,_w,h){pageImages.push({start:y,height:h});}};},
      toDataURL(){return "data:image/jpeg;base64,fixture";}
    };
  }
};
const window={
  html2canvas:async()=>({width:900,height:2300}),
  jspdf:{jsPDF:class{
    constructor(){this.internal={pageSize:{getWidth:()=>210,getHeight:()=>297}};}
    setProperties(){}addPage(){}addImage(){}setFont(){}
    setFontSize(){}setTextColor(){}text(){}
    output(){return new ArrayBuffer(8);}
  }}
};
vm.runInNewContext(src,{window,document,Blob},{timeout:1500});
(async()=>{
  const result=await window.TalenaPdfExport.exportSections(
    [{node:root,continuous:true}],{title:"Personlighet · Karaktärsdragsprofil",returnBlob:true}
  );
  assert.equal(result.type,"application/pdf");
  assert.equal(pageImages.length,2,
    "Three short trait sections should fit in two content pages");
  assert.equal(pageImages[0].start,0);
  assert.equal(pageImages.at(-1).start+pageImages.at(-1).height,2300);
  const cut=pageImages[0].start+pageImages[0].height;
  assert.ok(cut>=groups[0].to&&cut<=groups[1].from,
    "Break before Organisering instead of orphaning its header");
  for(const part of [...groups,{from:145,to:650}]){
    for(const page of pageImages.slice(0,-1)){
      const boundary=page.start+page.height;
      assert.ok(!(boundary>part.from&&boundary<part.to),
        "Do not cut a complete quick-profile section that fits A4");
    }
  }
  // Unrelated report types retain the existing 72%-fill rule.
  assert.equal(window.TalenaPdfExport.calculatePageSlices(2250,1000,[760,1780])[0].height,760);
  console.log("Quick trait PDF: no orphan category heading, whole sections/rows, two compact content pages");
})().catch(err=>{console.error(err);process.exitCode=1;});
