"use strict";
// Resultatsammanfattning (the text-only third Personality view):
// reproduce a page edge intersecting Kreativitet's heading/description.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const code=fs.readFileSync("static/js/talena/pdf-export-core.js","utf8");
const layout=fs.readFileSync("templates/customer/core/layouts/customer_base.html","utf8");
assert.match(layout,/candidate-report-export\.css' %}\?v=[a-zA-Z0-9_-]+/, "PDF stylesheet must use a versioned asset URL");
assert.ok(code.includes("getPersonalityDescriptionPageGuides"));
assert.ok(code.includes(".personality-description-quick-row,"),
  "Rows also need their own natural breakpoints");

const rect=(top,bottom)=>({
  getBoundingClientRect:()=>({top,bottom,height:bottom-top,width:900})
});
function section(top,headerBottom,positions) {
  const heading=rect(top,headerBottom);
  const rows=positions.map(([a,b])=>rect(a,b));
  return {
    heading,rows,
    querySelector(selector) {
      if(selector===".personality-quick-section__header")return heading;
      if(selector===".personality-description-quick-row")return rows[0]||null;
      return null;
    },
    querySelectorAll(selector) {
      return selector===".personality-description-quick-row"?rows:[];
    }
  };
}
// Exactly 18 character traits. Nominal A4 edge is around 1320px,
// which would bisect the Kreativitet row (1230–1350) without protection.
const groups=[
  section(125,165,[
    [180,282],[290,392],[400,502],[510,612],[620,722],[730,832]
  ]),
  section(860,900,[
    [915,1015],[1023,1123],[1131,1222],[1230,1350],
    [1358,1460],[1468,1570]
  ]),
  section(1610,1650,[
    [1665,1770],[1778,1880],[1888,1990],
    [1998,2100],[2108,2210],[2218,2340]
  ])
];
const descriptions={
  querySelectorAll(sel){
    return sel===".personality-description-section"?groups:[];
  }
};
const node={
  getBoundingClientRect:()=>({top:0,bottom:2400,height:2400,width:900}),
  closest:sel=>sel==='[data-candidate-pdf-report="personality-results"]'?{}:null,
  querySelector:sel=>sel===".personality-trait-descriptions-view"?descriptions:null,
  querySelectorAll(sel){
    if(sel==="img")return [];
    if(sel.includes(".personality-description-quick-row"))
      return groups.flatMap(group=>group.rows);
    return [];
  }
};
const pages=[];
const document={
  fonts:{ready:Promise.resolve()},
  documentElement:{clientWidth:1200},
  createElement(name){
    assert.equal(name,"canvas");
    return {width:0,height:0,
      getContext(){return {drawImage(_s,_x,from,_w,height){
        pages.push({start:from,height});
      }};},
      toDataURL(){return "data:image/jpeg;base64,fixture";}
    };
  }
};
const window={
  html2canvas:async()=>({width:900,height:2400}),
  jspdf:{jsPDF:class {
    constructor(){this.internal={pageSize:{getWidth:()=>210,getHeight:()=>297}};}
    setProperties(){}addPage(){}addImage(){}setFont(){}
    setFontSize(){}setTextColor(){}text(){}
    output(){return new ArrayBuffer(12);}
  }}
};
vm.runInNewContext(code,{document,window,Blob},{timeout:1500});
(async()=>{
  const pdf=await window.TalenaPdfExport.exportSections(
    [{node,continuous:true}],{title:"Personlighet Resultatsammanfattning",returnBlob:true}
  );
  assert.equal(pdf.type,"application/pdf");
  assert.equal(groups.flatMap(g=>g.rows).length,18);
  assert.equal(pages.length,2,"Should use the existing two content pages, not add a third");
  assert.equal(pages[0].start,0);
  assert.equal(pages.at(-1).start+pages.at(-1).height,2400);
  for(const page of pages.slice(0,-1)){
    const boundary=page.start+page.height;
    for(const g of groups){
      for(const row of g.rows){
        const b=row.getBoundingClientRect();
        assert.ok(!(boundary>b.top&&boundary<b.bottom),
          "Resultatsammanfattning must not split a trait heading from its description");
      }
      const first=g.rows[0].getBoundingClientRect();
      const heading=g.heading.getBoundingClientRect();
      assert.ok(!(boundary>heading.top&&boundary<first.bottom),
        "Category title must travel with its first row");
    }
  }
  const boundary=pages[0].start+pages[0].height;
  assert.ok(boundary>=1222&&boundary<=1230,
    "Break just before Kreativitet rather than inside its copy");

  // Other personality views and unrelated PDFs must keep old pagination.
  assert.equal(window.TalenaPdfExport.calculatePageSlices(2250,1000,[760,1780])[0].height,760);
  console.log("Personality text summary PDF: 18 rows intact, no orphan headings, 2 content pages");
})().catch(e=>{console.error(e);process.exitCode=1;});
