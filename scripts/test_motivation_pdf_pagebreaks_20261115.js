"use strict";

// #483: regression for the user's real Motivation PDF problem:
// the last top-driver card and 5-point factor scales must not be cut in half.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("static/js/talena/pdf-export-core.js", "utf8");
const pdfStyles = fs.readFileSync("static/css/talena/pages/candidate-report-export.css", "utf8");
const layout = fs.readFileSync("templates/customer/core/layouts/customer_base.html", "utf8");
// Only the full-page Motivation PDF frame disappears. Individual chart and
// factor cards remain styled in the assessment CSS, and screen UI is untouched.
assert.match(pdfStyles, /\[data-candidate-pdf-report="motivation-results"\] \.talena-candidate-pdf-body\.candidate-insight-page \{\s*border: 0 !important;\s*border-radius: 0 !important;\s*box-shadow: none !important;/);
assert.ok(layout.includes("20261115-motivation-questions-pdf-1"), "Bust old CSS cache for new PDF visuals");

function block(top, bottom) {
  return { getBoundingClientRect: () => ({
    top, bottom, height: bottom - top, width: 1000,
  }) };
}

function createMotivationFixture() {
  const chart = block(100, 1000);
  const firstTop = block(1150, 1320);
  const nextTop = block(1335, 1495);
  const lastTop = block(1510, 1680);
  const firstLow = block(1840, 2000);
  const secondLow = block(2010, 2150);
  const lastLow = block(2160, 2310);
  const firstFactor = block(2510, 2630);
  const secondFactor = block(2645, 2770);
  const thirdFactor = block(2785, 2920);
  const fourthFactor = block(2935, 3050);
  const fifthFactor = block(3065, 3180);
  const footer = block(3260, 3340);
  const summaryGroups = [
    {first:firstTop, heading:block(1070,1140)},
    {first:firstLow, heading:block(1760,1830)},
  ];
  const lists=summaryGroups.map(group=>({
    querySelector(selector) {
      return selector===".motivation-summary-item"?group.first:null;
    },
    closest(selector) {
      assert.equal(selector,"article");
      return { querySelector:()=>group.heading };
    },
  }));
  const ranges = [
    [100,1000], [1070,1320], [1335,1495], [1510,1680],
    [1760,2000], [2010,2150], [2160,2310], [2400,2630],
    [2645,2770], [2785,2920], [2935,3050], [3065,3180],
    [3260,3340],
  ];
  const body = {
    closest(selector) {
      return selector==='[data-candidate-pdf-report="motivation-results"]'
        ? {} : null;
    },
    getBoundingClientRect() {
      return {top:0, bottom:3600, width:1000,height:3600};
    },
    querySelectorAll(selector) {
      if (selector==="img") return [];
      if (selector===".motivation-summary-list")return lists;
      if (selector.includes(".motivation-visual-overview")) {
        return [
          chart,firstTop,nextTop,lastTop,firstLow,secondLow,lastLow,
          firstFactor,secondFactor,thirdFactor,fourthFactor,fifthFactor,footer
        ];
      }
      return [];
    },
    querySelector(selector) {
      if (selector===".motivation-full-profile-heading")return block(2400,2500);
      if (selector===".motivation-factor-list .motivation-factor-result")return firstFactor;
      return null;
    },
  };
  return {body,ranges};
}

async function checkEndToEnd() {
  const drawnPages=[];
  const browserWindow = {
    html2canvas:async()=>({width:1000,height:3600}),
    jspdf:{jsPDF:class {
      constructor(){
        this.internal={
          pageSize:{
            getWidth:()=>210,
            getHeight:()=>297,
          },
        };
      }
      setProperties(){}
      addPage(){}
      addImage(){}
      setFont(){}
      setFontSize(){}
      setTextColor(){}
      text(){}
      output(){return new ArrayBuffer(8);}
    }},
  };
  const doc={
    documentElement:{clientWidth:1200},
    fonts:{ready:Promise.resolve()},
    createElement(name) {
      assert.equal(name,"canvas");
      return {
        width:0,height:0,
        getContext(){return {
          drawImage(_source,_x,fromY,_w,height) {
            drawnPages.push({start:fromY,height});
          },
        };},
        toDataURL(){return "data:image/jpeg;base64,synthetic";}
      };
    },
  };
  vm.runInNewContext(source,{window:browserWindow,document:doc,Blob},{
    timeout:1000
  });
  const {body,ranges}=createMotivationFixture();
  const rendered=await browserWindow.TalenaPdfExport.exportSections(
    [{node:body,continuous:true}],
    {title:"Synthetic Motivation report",returnBlob:true}
  );
  assert.equal(rendered.type,"application/pdf");
  assert.ok(drawnPages.length>=3,"Fixture should span multiple pages");
  assert.equal(drawnPages[0].start,0);
  assert.equal(
    drawnPages[drawnPages.length-1].start+
    drawnPages[drawnPages.length-1].height,
    3600
  );
  for(let i=0;i<drawnPages.length;i++) {
    const p=drawnPages[i];
    if(i)assert.equal(p.start,drawnPages[i-1].start+drawnPages[i-1].height);
    if(i===drawnPages.length-1)continue;
    const boundary=p.start+p.height;
    const offenders=ranges.filter(([start,end])=>boundary>start&&boundary<end);
    assert.deepEqual(offenders,[],"A page cut through a motivation card/header");
  }

  const pure=browserWindow.TalenaPdfExport.calculatePageSlices;
  const longCard=pure(2300,1000,[],[{start:0,end:1400}]);
  assert.equal(longCard[0].height,1000,
    "Oversized single blocks must still advance, not create a loop");
  assert.equal(longCard.at(-1).start+longCard.at(-1).height,2300);

  const legacy=pure(2250,1000,[760,1780]);
  assert.equal(legacy[0].height,760,
    "Other reports must preserve the existing natural breakpoint behaviour");

  console.log("Motivation PDF page breaks: no split driver descriptions/scales, no orphan headings, old reports unchanged");
}
checkEndToEnd().catch(err=>{console.error(err);process.exitCode=1;});
