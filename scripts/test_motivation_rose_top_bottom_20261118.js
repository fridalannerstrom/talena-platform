"use strict";
// Highlights are derived from each actual rendered petal, not global
// "good/bad" colours. Both the on-screen and PDF canvas use this plugin.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = filename => fs.readFileSync(filename, "utf8");
const base = read("templates/customer/processes/process_base.html");
const theme = read("static/js/talena/candidate-chart-theme.js");
const html = read("templates/customer/processes/partials/candidate_insights/motivation/_results.html");
const css = read("static/css/talena/pages/candidate-charts.css");

assert.ok(html.includes('data-factor-highlight="{{ item.rose_highlight|default:\'\' }}"'));
assert.ok(html.includes("motivation_insights.less_central_drivers"));
assert.ok(html.includes("Mest framträdande (3) · mörkare nyans"));
assert.ok(html.includes("Minst framträdande (3) · ljusare nyans"));
assert.ok(html.includes("Darker shades of each petal"));
assert.ok(css.includes("background: #83766b"));
assert.ok(css.includes("background: #b9ada2"));
assert.ok(!css.includes("motivation-rose-chart__legend-outline"));
assert.ok(base.includes("window.TalenaPdfMotivationRose = Object.freeze({"));
assert.ok(base.includes("stage.append(chartRoot.cloneNode(true))"));
assert.ok(base.includes("const tipRadius ="));
assert.ok(base.includes("const dotX ="));
assert.ok(!base.includes("highlightStroke"));
assert.ok(/borderColor:\s*"#ffffff"/.test(base));
assert.ok(/hoverBorderColor:\s*"#ffffff"/.test(base));

// Keep the PDF-only initial palette aligned with the live Talena chart theme.
const palette = [
  [239, 94, 82], [207, 137, 127],
  [126, 162, 143], [197, 151, 79]
];
for(const rgb of palette) {
  assert.ok(base.includes("["+rgb.join(", ")+"]"));
  assert.ok(theme.includes("rgb: ["+rgb.join(", ")+"]"));
}
assert.ok(base.includes("2: 0.52") && base.includes("5: 0.96"));

// Extract actual project helper + renderer instead of reimplementing their logic.
const helperMatch = base.match(/  function roseAccentColour\(fill, rank\) \{[\s\S]*?\n  \}\n\n  const backgroundColours/);
assert.ok(helperMatch, "Missing dynamic per-petal colour helper");
const helperSource = helperMatch[0].slice(0, helperMatch[0].lastIndexOf("\n\n  const backgroundColours"));
const roseAccentColour = new Function("return " + helperSource)();
assert.equal(roseAccentColour("rgba(120, 140, 150, 0.5)", ""), null);
assert.equal(roseAccentColour("invalid", "top"), null);
const blendVisible = str => {
  const components = str.match(/[\d.]+/g).map(Number);
  return components.slice(0,3).map(v=>v*components[3]+255*(1-components[3]));
};
const parsed = str => str.match(/[\d.]+/g).map(Number);
const brightness = rgb => rgb.reduce((a,b)=>a+b,0);
for (const rgb of palette) {
  let previousLight = null;
  for (const opacity of [0.38, 0.52, 0.68, 0.84, 0.96]) {
    const fill = "rgba("+rgb.join(", ")+", "+opacity+")";
    const visible = blendVisible(fill);
    const darker = parsed(roseAccentColour(fill,"top"));
    const lighter = parsed(roseAccentColour(fill,"bottom"));
    assert.ok(darker.every((v,i)=>v<rgb[i]),
      "Top accent must darken its original domain colour");
    assert.ok(lighter.every((v,i)=>v>rgb[i]),
      "Bottom accent must be a lighter version of its domain colour");
    assert.ok(brightness(darker)<brightness(lighter),
      "Top should remain the stronger and bottom the softer mark");
    assert.ok(brightness(lighter)<660,
      "Bottom accent must retain enough pigment to show on a white canvas");
    if(opacity <= 0.68) {
      assert.ok(lighter.every((v,i)=>v<visible[i]),
        "On pale low-score petals, the soft accent must remain visible");
    }
    if(previousLight) {
      assert.deepEqual(lighter,previousLight,
        "Low-score transparency cannot bleach the bottom marker");
    }
    previousLight=lighter;
  }
}

const wrapMatch = base.match(/  function wrapLabel\(value, maxWidth, ctx\) \{[\s\S]*?\n  \}\n\n  \/\*/);
assert.ok(wrapMatch);
const wrapSource = wrapMatch[0].slice(0, wrapMatch[0].lastIndexOf("\n\n  /*"));
const wrapLabel = new Function("return " + wrapSource)();
const measure = value => ({width:value.length*7});
assert.deepEqual(wrapLabel("Självständighet",76,{measureText:measure}),["Självständighet"]);
assert.deepEqual(wrapLabel("Människors utveckling",90,{measureText:measure}),["Människors","utveckling"]);

const ranked = {top:[0,4,8],bottom:[1,6,11]};
const items = Array.from({length:20}, (_,i)=>({
  name:i===5?"Självständighet":"Drivkraft "+i,
  score:1+i%5,
  highlight:ranked.top.includes(i)?"top":ranked.bottom.includes(i)?"bottom":"",
  domainIndex:Math.floor(i/5),
}));
const fills = items.map(item => {
  const rgb=palette[item.domainIndex];
  const alpha=[0.38,0.52,0.68,0.84,0.96][item.score-1];
  return "rgba("+rgb.join(", ")+", "+alpha+")";
});
const arcs = items.map((_,i)=>({
  startAngle:i*Math.PI*2/20,
  endAngle:(i+1)*Math.PI*2/20,
  innerRadius:0,
  outerRadius:50+i*3,
  options:{},
}));
const pluginMatch=base.match(/const motivationRoseLabelsPlugin = ([\s\S]*?)\n\n\n  const chartInstance = new ChartLibrary/);
assert.ok(pluginMatch, "Expected motivation rose local afterDraw plugin");
const pluginSource=pluginMatch[1].trim().replace(/;$/,"");
const plugin=new Function(
  "items","domainGroups","narrow","compact","wrapLabel","roseAccentColour",
  "return ("+pluginSource+")"
)(items,[{startIndex:0},{startIndex:5},{startIndex:10},{startIndex:15}],
  false,false,wrapLabel,roseAccentColour);
const drawOps=[];
const ctx={
  beginPath(){this.lastArc=null;this.lastLine=null;},
  save(){},restore(){},
  moveTo(...args){this.lastLine=args;},
  lineTo(...args){this.lastLine=[...(this.lastLine||[]),...args];},
  arc(x,y,r,start,end){this.lastArc={x,y,r,start,end};},
  stroke(){drawOps.push({kind:"stroke",colour:this.strokeStyle,
    arc:this.lastArc,line:this.lastLine});},
  fill(){drawOps.push({kind:"fill",colour:this.fillStyle,arc:this.lastArc});},
  fillText(value,x,y,maxWidth){drawOps.push({kind:"text",value,x,y,maxWidth});},
  measureText:measure,
};
const chart={
  data:{datasets:[{backgroundColor:fills}]},
  getDatasetMeta:()=>({data:arcs}),
  scales:{r:{xCenter:350,yCenter:350,drawingArea:190}},
  ctx,
};
const assertDraw=()=>{
  drawOps.length=0;
  plugin.afterDraw(chart);
  const tipStrokes=drawOps.filter(op=>op.kind==="stroke"&&/^rgb\(/.test(op.colour));
  const dots=drawOps.filter(op=>op.kind==="fill"&&/^rgb\(/.test(op.colour));
  const highlighted=items.map((item,i)=>({...item,index:i}))
    .filter(item=>item.highlight);
  assert.equal(tipStrokes.length,6);
  assert.equal(dots.length,6);
  // Identical factors from the same domain can legitimately have the
  // same tone; distinct domains must not collapse to two global colours.
  assert.ok(new Set(tipStrokes.map(op=>op.colour)).size>=3);
  highlighted.forEach((item,i)=>{
    const expected=roseAccentColour(chart.data.datasets[0].backgroundColor[item.index],item.highlight);
    assert.equal(tipStrokes[i].colour,expected);
    assert.equal(dots[i].colour,expected);
  });
  assert.ok(tipStrokes.every(op=>op.arc&&!op.line&&op.arc.end-op.arc.start>0));
  assert.ok(tipStrokes.every(op=>op.arc.end-op.arc.start<Math.PI*2/20));
  assert.ok(dots.every(op=>op.arc&&op.arc.r<=4));
  assert.ok(drawOps.some(op=>op.kind==="text"&&op.value==="Självständighet"));
};
assertDraw();
// A theme/palette update after render must recompute, not freeze the colours.
chart.data.datasets[0].backgroundColor=fills.map((fill,i)=>
  fill.replace(/,\s*0\.[\d]+\)$/,", 0.96)")
);
assertDraw();

// The separate chart theme still maintains white radial boundaries.
const labels=items.map(item=>({dataset:{
  factorNameSv:item.name,factorNameEn:item.name,
  factorScore:String(item.score),domainIndex:String(item.domainIndex),
  factorDomainSv:"Tillhörighet",factorHighlight:item.highlight,
}}));
const root={querySelectorAll:selector=>
  selector==="[data-motivation-rose-item]"?labels:[]};
const canvas={
  clientWidth:780,
  matches:selector=>selector==="[data-motivation-rose-chart]",
  closest:selector=>selector==="[data-motivation-rose-chart-root]"?root:null,
};
const dataset={borderWidth:3};
const liveChart={
  canvas,data:{datasets:[dataset]},
  getDatasetMeta:()=>({data:arcs}),
  options:{scales:{r:{ticks:{},grid:{}}},layout:{}},
  config:{plugins:[{id:"motivationRoseLabels",afterDraw(){}}]},
  draw(){},update(){this.draw();},
};
canvas._motivationRoseChartInstance=liveChart;
const scheduled=[];
const document={
  readyState:"complete",documentElement:{lang:"sv"},
  querySelectorAll:selector=>selector==="[data-motivation-rose-chart]"?[canvas]:[],
  addEventListener(){},
};
const window={setTimeout:fn=>scheduled.push(fn)};
vm.runInNewContext(theme,{document,window},{timeout:1000});
scheduled[0]();
assert.equal(liveChart.$talenaBrandTheme,true);
assert.equal(dataset.borderColor,"#ffffff");
assert.equal(dataset.hoverBorderColor,"#ffffff");
assert.ok(arcs.every(arc=>arc.options.borderColor==="#ffffff"));
liveChart.draw();
assert.ok(arcs.every(arc=>arc.options.hoverBorderColor==="#ffffff"));

console.log("Motivation rose uses darker/lighter variants of each rendered petal, including PDF palette and redraw");
