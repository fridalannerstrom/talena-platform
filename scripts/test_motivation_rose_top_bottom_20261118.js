"use strict";
// #435 / motivation rose: top three and bottom three get an outline around
// the whole petal, in a darker shade of its own domain colour. No tip arcs
// or name dots. Both initial/PDF rendering and live theme must agree.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = filename => fs.readFileSync(filename, "utf8");
const base = read("templates/customer/processes/process_base.html");
const theme = read("static/js/talena/candidate-chart-theme.js");
const html = read("templates/customer/processes/partials/candidate_insights/motivation/_results.html");
const css = read("static/css/talena/pages/candidate-charts.css");

assert.ok(html.includes('data-factor-highlight="{{ item.rose_highlight|default:\'\'}"'));
assert.ok(html.includes("motivation_insights.less_central_drivers"));
assert.ok(html.includes("Mest framträdande (3)"));
assert.ok(html.includes("Minst framträdande (3)"));
assert.ok(html.includes("motivation-rose-chart__legend-line--top"));
assert.ok(html.includes("motivation-rose-chart__legend-line--bottom"));
assert.ok(!html.includes("motivation-rose-chart__legend-dot"));
assert.ok(css.includes("border-top-width: 3px"));
assert.ok(css.includes("border-top-width: 1.5px"));
assert.ok(!css.includes("motivation-rose-chart__legend-dot"));
assert.ok(!base.includes("const tipRadius ="));
assert.ok(!base.includes("const dotX ="));
assert.ok(!base.includes("highlightColours"));
assert.ok(base.includes("window.TalenaPdfMotivationRose = Object.freeze({"));
assert.ok(base.includes("stage.append(chartRoot.cloneNode(true))"));
assert.ok(/borderColor:\s*petalBorderColours/.test(base));
assert.ok(/hoverBorderColor:\s*petalBorderColours/.test(base));
assert.ok(/borderWidth:\s*petalBorderWidths/.test(base));
assert.ok(/hoverBorderWidth:\s*petalBorderWidths/.test(base));

// Extract the real helper from the candidate renderer.
const helperMatch = base.match(/  function roseAccentColour\(fill, rank\) \{[\s\S]*?\n  \}\n\n  const backgroundColours/);
assert.ok(helperMatch, "Missing darkened per-petal accent helper");
const helper = helperMatch[0].slice(0, helperMatch[0].lastIndexOf("\n\n  const backgroundColours"));
const accent = new Function("return " + helper)();
assert.equal(accent("rgba(120, 140, 150, 0.5)", ""), null);
assert.equal(accent("invalid", "top"), null);
const palette = [[239,94,82],[207,137,127],[126,162,143],[197,151,79]];
const rgb = str => str.match(/[\d.]+/g).map(Number);
for (const colour of palette) {
  const accents = [];
  for (const alpha of [0.38, 0.52, 0.68, 0.84, 0.96]) {
    const fill = "rgba(" + colour.join(", ") + ", " + alpha + ")";
    const top = rgb(accent(fill, "top"));
    const bottom = rgb(accent(fill, "bottom"));
    assert.ok(top.every((n,i) => n < bottom[i] && bottom[i] < colour[i]),
      "Both borders should darken the base colour, top a little more");
    accents.push([top,bottom]);
  }
  for (const item of accents.slice(1)) assert.deepEqual(item,accents[0],
    "Low-opacity petals must retain the same legible border colour");
}

// Evaluate the original Chart.js/PDF dataset style declarations.
const ranked = {top:[0,4,8],bottom:[1,6,11]};
const items = Array.from({length:20},(_,i)=>({
  name:i===5?"Självständighet":"Drivkraft "+i,
  score:i%5+1,
  highlight:ranked.top.includes(i)?"top":ranked.bottom.includes(i)?"bottom":"",
  domainIndex:Math.floor(i/5),
}));
const backgroundColours = items.map(item => {
  const col=palette[item.domainIndex];
  const opacity=[0.38,0.52,0.68,0.84,0.96][item.score-1];
  return "rgba("+col.join(", ")+", "+opacity+")";
});
const a=base.indexOf("  const petalBorderColours =");
const z=base.indexOf("  /*\n   * Group contiguous factors",a);
assert.ok(a>0 && z>a, "Initial/PDF border declarations must exist");
const styleBlock=base.slice(a,z);
const computeInitial = new Function("items","backgroundColours","compact","roseAccentColour",
  styleBlock+"return {colors:petalBorderColours,widths:petalBorderWidths};");
const initial=computeInitial(items,backgroundColours,false,accent);
const compact=computeInitial(items,backgroundColours,true,accent);
assert.equal(initial.colors.length,20);
assert.equal(initial.widths.length,20);
assert.equal(compact.colors.length,20);
items.forEach((item,i)=>{
  assert.equal(initial.colors[i],accent(backgroundColours[i],item.highlight)||"#ffffff");
  assert.equal(compact.colors[i],initial.colors[i]);
  assert.equal(initial.widths[i],item.highlight==="top"?2.6:item.highlight==="bottom"?1.6:3);
  assert.equal(compact.widths[i],item.highlight==="top"?2:item.highlight==="bottom"?1.3:2);
});
assert.equal(initial.colors.filter(c=>c==="#ffffff").length,14);

// Smoke-test the live theme and its direct Chart.js arc options, including
// hover; the adapter used to overwrite all outlines with white.
const labels=items.map(item=>({dataset:{
  factorNameSv:item.name,factorNameEn:item.name,
  factorScore:String(item.score),
  domainIndex:String(item.domainIndex),
  factorDomainSv:"Tillhörighet",factorHighlight:item.highlight,
}}));
const root={querySelectorAll:q=>q==="[data-motivation-rose-item]"?labels:[]};
const arcs=items.map(()=>({options:{}}));
const canvas={
  clientWidth:780,
  matches:q=>q==="[data-motivation-rose-chart]",
  closest:q=>q==="[data-motivation-rose-chart-root]"?root:null,
};
const dataset={borderWidth:3};
const chart={
  canvas,data:{datasets:[dataset]},
  getDatasetMeta:()=>({data:arcs}),
  options:{scales:{r:{ticks:{},grid:{}}},layout:{}},
  config:{plugins:[{id:"motivationRoseLabels",afterDraw(){}}]},
  draw(){},update(){this.draw();},
};
canvas._motivationRoseChartInstance=chart;
const scheduled=[];
const document={
  readyState:"complete",documentElement:{lang:"sv"},
  querySelectorAll:q=>q==="[data-motivation-rose-chart]"?[canvas]:[],
  addEventListener(){},
};
const window={setTimeout:fn=>scheduled.push(fn)};
vm.runInNewContext(theme,{document,window},{timeout:1000});
assert.ok(scheduled.length>0);
scheduled[0]();
assert.equal(chart.$talenaBrandTheme,true);
assert.deepEqual(Array.from(dataset.borderColor),initial.colors);
assert.deepEqual(Array.from(dataset.borderWidth),initial.widths);
assert.deepEqual(Array.from(dataset.hoverBorderColor),initial.colors);
assert.deepEqual(Array.from(dataset.hoverBorderWidth),initial.widths);
arcs.forEach((arc,i)=>{
  assert.equal(arc.options.borderColor,initial.colors[i]);
  assert.equal(arc.options.hoverBorderColor,initial.colors[i]);
  assert.equal(arc.options.borderWidth,initial.widths[i]);
  assert.equal(arc.options.hoverBorderWidth,initial.widths[i]);
});
chart.draw();
assert.ok(arcs.every((arc,i)=>arc.options.borderColor===initial.colors[i]));
assert.ok(theme.includes("applyRenderedArcTheme(chart, colours);"),
  "The unrelated team-style chart must still use its own white borders");

// The full petal outline should not alter long label wrapping.
const wrapMatch=base.match(/  function wrapLabel\(value, maxWidth, ctx\) \{[\s\S]*?\n  \}\n\n  \/\*/);
assert.ok(wrapMatch);
const wrapLabel=new Function("return "+wrapMatch[0].slice(0,wrapMatch[0].lastIndexOf("\n\n  /*")))();
const measureText=value=>({width:value.length*7});
assert.deepEqual(wrapLabel("Självständighet",76,{measureText}),["Självständighet"]);

console.log("Motivation rose: 3 strong + 3 subtle full-petal outlines, PDF colours, no dots/tips, and hover styling OK");
