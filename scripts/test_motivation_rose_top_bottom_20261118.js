"use strict";
// Motivation rose: server-ranked top/bottom 3, same palette on hover/PDF,
// and no mid-word break in labels such as Självständighet.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const read = path => fs.readFileSync(path, "utf8");
const theme = read("static/js/talena/candidate-chart-theme.js");
const base = read("templates/customer/processes/process_base.html");
const html = read("templates/customer/processes/partials/candidate_insights/motivation/_results.html");
const styles = read("static/css/talena/pages/candidate-charts.css");

assert.ok(html.includes('data-factor-highlight="{{ item.rose_highlight|default:\'\' }}"'));
assert.ok(html.includes("motivation-rose-chart__legend-outline--top"));
assert.ok(html.includes("motivation-rose-chart__legend-outline--bottom"));
assert.ok(html.includes("motivation_insights.less_central_drivers"),
  "Bottom 3 list and chart must follow one backend ranking");
assert.ok(styles.includes("border-color: #c4574b"));
assert.ok(styles.includes("border-color: #276f62"));
assert.ok(base.includes("window.TalenaPdfMotivationRose = Object.freeze({"));
assert.ok(base.includes("stage.append(chartRoot.cloneNode(true))"),
  "PDF must clone the same highlighted rose as the candidate view");
assert.ok(base.includes('highlight: ["top", "bottom"].includes(element.dataset.factorHighlight)'),
  "The initial chart and offscreen PDF must read the ranked highlights");
assert.ok(/borderColor:\s*roseBorders/.test(base),
  "The initial chart must draw highlighted petals without waiting for the theme pass");
assert.ok(/hoverBorderColor:\s*roseBorders/.test(base),
  "The PDF and hover states should retain the rank outlines");
assert.ok(html.includes("Coral outlines mark the three highest drivers"),
  "Screen reader label must explain the outline meaning");

const wrapMatch = base.match(/  function wrapLabel\(value, maxWidth, ctx\) \{[\s\S]*?\n  \}\n\n  \/\*/);
assert.ok(wrapMatch, "Motivation label wrapper must exist");
const wrapSource = wrapMatch[0].slice(0, wrapMatch[0].lastIndexOf("\n\n  /*"));
const wrapLabel = new Function("return " + wrapSource)();
const ctx = {measureText: value => ({width: value.length * 7})};
assert.deepEqual(wrapLabel("Självständighet", 76, ctx), ["Självständighet"]);
assert.deepEqual(wrapLabel("Människors utveckling", 90, ctx),
  ["Människors", "utveckling"]);
assert.ok(base.includes("labelMaxWidth\n              );"),
  "Use canvas maximum drawing width rather than splitting a long word");

const ranked = {top:[0,4,8], bottom:[1,6,11]};
const labels = Array.from({length:20}, (_,i) => ({
  dataset: {
    factorNameSv: i===5 ? "Självständighet" : "Drivkraft "+i,
    factorNameEn: "Factor "+i,
    factorScore: String((i%5)+1),
    domainIndex: String(Math.floor(i/5)),
    factorDomainSv: "Tillhörighet",
    factorHighlight: ranked.top.includes(i) ? "top" :
      ranked.bottom.includes(i) ? "bottom" : "",
  },
}));
const root = {
  querySelectorAll: selector =>
    selector==="[data-motivation-rose-item]" ? labels : [],
};
const arcs = Array.from({length:20}, () => ({options:{}}));
const canvas = {
  clientWidth:780,
  matches: selector=>selector==="[data-motivation-rose-chart]",
  closest: selector=>selector==="[data-motivation-rose-chart-root]"
    ? root : null,
};
const plugin = {id:"motivationRoseLabels", afterDraw(){}};
const dataset = {borderWidth:3};
const chart = {
  canvas,
  data:{datasets:[dataset]},
  getDatasetMeta:()=>({data:arcs}),
  options:{scales:{r:{ticks:{},grid:{}}},layout:{}},
  config:{plugins:[plugin]},
  draw(){},
  update(){this.draw();},
};
canvas._motivationRoseChartInstance=chart;
const scheduled=[];
const document = {
  readyState:"complete",documentElement:{lang:"sv"},
  querySelectorAll:selector=>selector==="[data-motivation-rose-chart]"?[canvas]:[],
  addEventListener(){},
};
const window = {setTimeout:fn=>scheduled.push(fn)};
vm.runInNewContext(theme, {document,window}, {timeout:1000});
assert.ok(scheduled.length,"Motivation theme should schedule a draw");
scheduled[0]();
assert.equal(chart.$talenaBrandTheme,true);
assert.equal(arcs.filter(x=>x.options.borderColor==="#c4574b").length,3);
assert.equal(arcs.filter(x=>x.options.borderColor==="#276f62").length,3);
assert.equal(arcs.filter(x=>x.options.borderColor==="#ffffff").length,14);
assert.equal(dataset.borderColor.length,20);
assert.equal(arcs[0].options.borderColor,arcs[0].options.hoverBorderColor);
chart.draw(); // ensure highlights survive after re-render/hover
assert.equal(arcs[0].options.borderColor,"#c4574b");
assert.equal(arcs[1].options.borderColor,"#276f62");
assert.equal(arcs[2].options.borderColor,"#ffffff");
console.log("Motivation rose top/bottom 3 strokes, legend, PDF clone and word wrapping OK");
