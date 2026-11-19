"use strict";
// Guard the trait+indicator portrait PDF against orphaned trait headings and
// cut STEN rows. The branded cover and screen presentation are unaffected.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const src=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");
const css=fs.readFileSync("static/css/talena/pages/candidate-report-export.css","utf8");
const layout=fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
const selector='[data-candidate-pdf-report="personality-results"]';
const rule=selector+' .talena-candidate-pdf-body.candidate-insight-page {';
assert.ok(css.includes(rule)&&layout.includes("20261119-manager-pdf-polish-8"));
const frame=css.slice(css.indexOf(rule),css.indexOf("}",css.indexOf(rule)));
for (const value of ["border:0 !important;","box-shadow:none !important;","padding:0 !important;"])
  assert.ok(frame.includes(value),"Personality PDF must omit the extra outer frame/padding");

const rect=(top,bottom)=>({getBoundingClientRect(){return {top,bottom,height:bottom-top,width:900};}});
const trait=(from,mainEnd,summaryEnd,rowEnds)=>{
  const heading=rect(from,from+65),main=rect(from+66,mainEnd);
  const summary=rect(mainEnd+6,summaryEnd);
  const rows=rowEnds.reduce((r,end)=>{const start=r.length?r.at(-1).getBoundingClientRect().bottom+12:summaryEnd+12;r.push(rect(start,end));return r;},[]);
  return {
    heading,main,summary,rows,
    querySelector(selector){
      if(selector===".personality-trait-card__header")return heading;
      if(selector===".personality-trait-card__main")return main;
      if(selector===".personality-trait-card__summary")return summary;
      if(selector===".personality-indicator-row")return rows[0]||null;
      return null;
    },
    querySelectorAll(selector){return selector===".personality-indicator-row"?rows:[];}
  };
};
const traits=[
  trait(150,375,430,[555,690,820]),
  trait(855,1080,1150,[1300,1450,1600]),
  trait(1645,1820,1885,[2020,2165,2325]),
  trait(2360,2530,2580,[2720,2870,3000]),
];
const groupTitles=[rect(90,145),rect(1610,1640)];
const sections=[
 {querySelector(selector){
   if(selector===".personality-profile-section__header")return groupTitles[0];
   if(selector===".personality-trait-card")return traits[0];
   return null;
 }},
 {querySelector(selector){
   if(selector===".personality-profile-section__header")return groupTitles[1];
   if(selector===".personality-trait-card")return traits[2];
   return null;
 }}
];
const node={
  getBoundingClientRect(){return {top:0,bottom:3100,height:3100,width:900};},
  closest(value){return value==='[data-candidate-pdf-report="personality-results"]'?{}:null;},
  querySelectorAll(q){
    if(q==="img")return [];
    if(q===".personality-profile-section")return sections;
    if(q===".personality-trait-card")return traits;
    if(q.startsWith(".team-report-pdf-part"))return [];
    return [];
  }
};
const drawn=[];
const document={
  documentElement:{clientWidth:1200},fonts:{ready:Promise.resolve()},
  createElement(name){
    assert.equal(name,"canvas");
    return {
      width:0,height:0,
      getContext(){return {drawImage(_c,_x,start,_w,height){drawn.push({start,height});}};},
      toDataURL(){return "data:image/jpeg;base64,fixture";}
    };
  }
};
const window={
  html2canvas:async()=>({width:900,height:3100}),
  jspdf:{jsPDF:class{
    constructor(){this.internal={pageSize:{getWidth:()=>210,getHeight:()=>297}};}
    setProperties(){} addPage(){} addImage(){} setFont(){}
    setFontSize(){} setTextColor(){} text(){}
    output(){return new ArrayBuffer(12);}
  }}
};
vm.runInNewContext(src,{document,window,Blob},{timeout:1500});

(async()=>{
  const pdf=await window.TalenaPdfExport.exportSections(
    [{node,continuous:true}],{title:"Synthetic Personality results",returnBlob:true}
  );
  assert.equal(pdf.type,"application/pdf");
  assert.ok(drawn.length>=3,"A long trait profile should span pages");
  const breakpoints=drawn.slice(0,-1).map(p=>p.start+p.height);
  for(const boundary of breakpoints) {
    for(const t of traits){
      // A page must not cut title, graph, summary and first indicator.
      const start=t.heading.getBoundingClientRect().top;
      const firstEnd=t.rows[0].getBoundingClientRect().bottom;
      assert.ok(!(boundary>start&&boundary<firstEnd),
        "A personality trait's initial score and first indicator were split");
      for(const row of t.rows){
        const box=row.getBoundingClientRect();
        assert.ok(!(boundary>box.top&&boundary<box.bottom),
          "An indicator's poles/STEN scale were split");
      }
    }
    assert.ok(!(boundary>groupTitles[1].getBoundingClientRect().top &&
      boundary<traits[2].summary.getBoundingClientRect().bottom),
      "Category heading should travel with the next trait's introduction");
  }
  assert.equal(drawn[0].start,0);
  for(let i=1;i<drawn.length;i++)
    assert.equal(drawn[i].start,drawn[i-1].start+drawn[i-1].height);
  assert.equal(drawn.at(-1).start+drawn.at(-1).height,3100);
  assert.equal(window.TalenaPdfExport.calculatePageSlices(2250,1000,[760,1780])[0].height,760,
    "Other report pagination remains unchanged");
  console.log("Personality PDF: trait intros, section headings and full STEN indicator rows stay intact");
})().catch(error=>{console.error(error);process.exitCode=1;});
