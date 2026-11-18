"use strict";
// #435 follow-up: quiet tip arcs + label dots for top/bottom three motivation
// factors. Existing domain colours and white radial separations are unchanged.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = path => fs.readFileSync(path, "utf8");
const theme = read("static/js/talena/candidate-chart-theme.js");
const base = read("templates/customer/processes/process_base.html");
const html = read("templates/customer/processes/partials/candidate_insights/motivation/_results.html");
const styles = read("static/css/talena/pages/candidate-charts.css");

assert.ok(html.includes('data-factor-highlight="{{ item.rose_highlight|default:\'\' }}"'));
assert.ok(html.includes("motivation-rose-chart__legend-dot--top"));
assert.ok(html.includes("motivation-rose-chart__legend-dot--bottom"));
assert.ok(html.includes("motivation_insights.less_central_drivers"),
  "Bottom 3 chart and text must use the same STIVE order");
assert.ok(styles.includes("background: #c4574b"));
assert.ok(styles.includes("background: #276f62"));
assert.ok(!styles.includes("motivation-rose-chart__legend-outline"));
assert.ok(html.includes("Coral accents mark the three highest drivers"),
  "The accessible description should explain the new visual markers");
assert.ok(base.includes("window.TalenaPdfMotivationRose = Object.freeze({"));
assert.ok(base.includes("stage.append(chartRoot.cloneNode(true))"),
  "The PDF must clone and render the same chart and highlight data");
assert.ok(base.includes("const tipRadius ="));
assert.ok(base.includes("const dotX ="));
assert.ok(!base.includes("roseBorders"), "Do not highlight the entire radial edge");
assert.ok(/borderColor:\s*"#ffffff"/.test(base));
assert.ok(/hoverBorderColor:\s*"#ffffff"/.test(base));

const wrapMatch = base.match(/  function wrapLabel\(value, maxWidth, ctx\) \{[\s\S]*?\n  \}\n\n  \/\*/);
assert.ok(wrapMatch, "Motivation label wrapper must exist");
const wrapSource = wrapMatch[0].slice(0, wrapMatch[0].lastIndexOf("\n\n  /*"));
const wrapLabel = new Function("return " + wrapSource)();
const measure = value => ({ width: value.length * 7 });
assert.deepEqual(wrapLabel("Självständighet", 76, {measureText:measure}), ["Självständighet"]);
assert.deepEqual(wrapLabel("Människors utveckling", 90, {measureText:measure}),
  ["Människors", "utveckling"]);

// Exercise the real Chart.js afterDraw plugin, not just string matching.
// It paints six coloured tip arcs and six matching dots, but zero coloured
// radial sides or complete petal outlines.
const ranked = {top:[0,4,8], bottom:[1,6,11]};
const items = Array.from({length:20}, (_,i) => ({
  name:i===5 ? "Självständighet" : "Drivkraft "+i,
  score:1 + i%5,
  highlight:ranked.top.includes(i) ? "top" : ranked.bottom.includes(i) ? "bottom" : "",
  domainIndex:Math.floor(i/5),
}));
const arcs = items.map((_,i) => ({
  startAngle:i*Math.PI*2/20,
  endAngle:(i+1)*Math.PI*2/20,
  innerRadius:0,
  outerRadius:50 + i*3,
  options:{},
}));
const pluginMatch = base.match(/const motivationRoseLabelsPlugin = ([\s\S]*?)\n\n\n  const chartInstance = new ChartLibrary/);
assert.ok(pluginMatch, "Expected the embedded rose drawing plugin");
const pluginSource = pluginMatch[1].trim().replace(/;$/, "");
const palette = {top:"#c4574b", bottom:"#276f62"};
const plugin = new Function(
  "items","domainGroups","narrow","compact","wrapLabel","highlightStroke",
  "return (" + pluginSource + ")"
)(items, [{startIndex:0},{startIndex:5},{startIndex:10},{startIndex:15}],
  false,false,wrapLabel,palette);
const draws=[];
const ctx={
  beginPath(){this.lastArc=null;this.lastLine=null;},
  save(){},restore(){},
  moveTo(...args){this.lastLine=args;},
  lineTo(...args){this.lastLine=[...(this.lastLine||[]),...args];},
  arc(x,y,r,start,end){this.lastArc={x,y,r,start,end};},
  stroke(){draws.push({kind:"stroke",colour:this.strokeStyle,
    width:this.lineWidth,arc:this.lastArc,line:this.lastLine});},
  fill(){draws.push({kind:"fill",colour:this.fillStyle,arc:this.lastArc});},
  fillText(value,x,y,maxWidth){draws.push({kind:"text",value,x,y,maxWidth});},
  measureText:measure,
};
const chart={
  getDatasetMeta:()=>({data:arcs}),
  scales:{r:{xCenter:350,yCenter:350,drawingArea:190}},
  ctx,
};
plugin.afterDraw(chart);
const tipStrokes=draws.filter(x=>x.kind==="stroke"&&
  [palette.top,palette.bottom].includes(x.colour));
const dots=draws.filter(x=>x.kind==="fill"&&
  [palette.top,palette.bottom].includes(x.colour));
assert.equal(tipStrokes.length,6);
assert.equal(tipStrokes.filter(x=>x.colour===palette.top).length,3);
assert.equal(tipStrokes.filter(x=>x.colour===palette.bottom).length,3);
assert.ok(tipStrokes.every(x=>x.arc && !x.line && x.arc.end-x.arc.start>0),
  "Each accent must be a short circular tip, never a radial side");
assert.ok(tipStrokes.every(x=>x.arc.end-x.arc.start<Math.PI*2/20),
  "Do not outline a full petal");
assert.equal(dots.length,6);
assert.equal(dots.filter(x=>x.colour===palette.top).length,3);
assert.equal(dots.filter(x=>x.colour===palette.bottom).length,3);
assert.ok(dots.every(x=>x.arc && x.arc.r<=4));
assert.ok(draws.some(x=>x.kind==="text"&&x.value==="Självständighet"));
assert.ok(draws.every(x=>!x.arc || Number.isFinite(x.arc.r)));

// The separate chart theme is allowed to change the domain fill colours,
// but it must keep every side separator white through hover/re-draw.
const labels=items.map((item,i)=>({
  dataset:{
    factorNameSv:item.name,factorNameEn:item.name,
    factorScore:String(item.score),domainIndex:String(item.domainIndex),
    factorDomainSv:"Tillhörighet",factorHighlight:item.highlight,
  },
}));
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
assert.ok(scheduled.length,"Chart theme should schedule its initial draw");
scheduled[0]();
assert.equal(liveChart.$talenaBrandTheme,true);
assert.equal(dataset.borderColor,"#ffffff");
assert.equal(dataset.hoverBorderColor,"#ffffff");
assert.ok(arcs.every(x=>x.options.borderColor==="#ffffff"));
assert.ok(arcs.every(x=>x.options.hoverBorderColor==="#ffffff"));
liveChart.draw();
assert.ok(arcs.every(x=>x.options.borderColor==="#ffffff"));

console.log("Motivation rose tip arcs, name dots, neutral borders, PDF path and word wrapping OK");
