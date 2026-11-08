// #375: composite chart mode switching, data source and anonymity contract.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const js = fs.readFileSync("static/js/talena/team-pages.js", "utf8");
const tpl = fs.readFileSync("templates/customer/teams/team_detail.html", "utf8");
const backend = fs.readFileSync("apps/teams/team_report_views.py", "utf8");
const css = fs.readFileSync("static/css/talena/pages/team-polish.css", "utf8");
const pdf = fs.readFileSync("static/js/talena/team-report-export.js", "utf8");

for (const id of ["team-style-chart-labels", "team-style-chart-averages",
  "team-style-chart-min", "team-style-chart-max"]) {
  assert.ok(tpl.includes(id), "missing source data: " + id);
}
for (const mode of ["average", "minimum", "maximum"]) {
  assert.ok(tpl.includes('data-team-chart-mode="' + mode + '"'));
}
assert.ok(backend.includes('"chart_min_values"'));
assert.ok(backend.includes('"minimum_rows"'));
assert.ok(!js.includes("readTeamStyleMinimumValues"), "minimum must come from backend, not table scraping");
assert.ok(css.includes("team-analytics-grid--composite"));
assert.ok(tpl.includes("data-team-chart-person-details"));
assert.ok(pdf.includes('node.querySelectorAll("[data-team-chart-person-details]")'),
  "anonymous PDF must exclude identity attribution");

// Run the real chart initialiser with a minimal mock DOM/Chart.js runtime.
const modeButtons = ["average", "minimum", "maximum"].map(mode => ({
  dataset: { teamChartMode: mode },
  classList: { toggle() {} },
  attrs: {},
  setAttribute(name, value) { this.attrs[name] = value; },
  addEventListener(name, callback) { this[name] = callback; }
}));
const peoplePanels = ["minimum", "maximum"].map(mode => ({
  dataset: { teamChartPeopleMode: mode },
  hidden: true
}));
const people = {
  hidden: true,
  querySelectorAll: () => peoplePanels
};
const description = { textContent: "" };
const section = {
  dataset: {},
  querySelectorAll: () => modeButtons,
  querySelector(selector) {
    if (selector === "[data-team-chart-description]") return description;
    if (selector === "[data-team-chart-person-details]") return people;
    return null;
  }
};
const canvas = {
  dataset: {
    averageLabel: "Medelvärde",
    minimumLabel: "Minimum",
    maximumLabel: "Maximum",
    averageHelp: "Average help",
    minimumHelp: "Minimum help",
    maximumHelp: "Maximum help"
  },
  closest: () => section
};
let chart = null;
class MockChart {
  constructor(element, config) {
    chart = this;
    this.element = element;
    this.config = config;
    this.updates = 0;
  }
  update() { this.updates += 1; }
}
const fixtures = {
  "team-style-chart-labels": ["Catalyst", "Director"],
  "team-style-chart-averages": [2.5, 3.5],
  "team-style-chart-min": [1.5, 2.5],
  "team-style-chart-max": [4.0, 5.0]
};
const sandbox = {
  document: { getElementById: id => id === "teamStyleAverageChart" ? canvas : null },
  window: { Chart: MockChart },
  readJsonScript: id => fixtures[id] || [],
  getTeamStyleLabelMap: () => ({ Catalyst: "Katalysator", Director: "Ledare" })
};
const start = js.indexOf("  function initTeamStyleChart() {");
const end = js.indexOf("  function initTeamModelGuide() {", start);
assert.ok(start >= 0 && end > start, "unable to find composite chart implementation");
const initializer = vm.runInNewContext("(" + js.slice(start, end).trim() + ")", sandbox);
initializer();
assert.ok(chart, "Chart.js should initialise");
assert.equal(chart.config.type, "radar");
assert.equal(chart.config.data.datasets.length, 1, "do not overlay datasets");
assert.deepEqual(Array.from(chart.config.data.datasets[0].data), [2.5, 3.5]);
assert.equal(chart.config.options.scales.r.startAngle, -22.5);
assert.equal(people.hidden, true);

modeButtons[1].click();
assert.equal(section.dataset.teamChartActiveMode, "minimum");
assert.deepEqual(Array.from(chart.config.data.datasets[0].data), [1.5, 2.5]);
assert.equal(chart.config.data.datasets.length, 1);
assert.equal(people.hidden, false);
assert.equal(peoplePanels[0].hidden, false);
assert.equal(peoplePanels[1].hidden, true);
assert.equal(description.textContent, "Minimum help");
assert.equal(modeButtons[1].attrs["aria-pressed"], "true");

modeButtons[2].click();
assert.deepEqual(Array.from(chart.config.data.datasets[0].data), [4, 5]);
assert.equal(peoplePanels[0].hidden, true);
assert.equal(peoplePanels[1].hidden, false);

modeButtons[0].click();
assert.deepEqual(Array.from(chart.config.data.datasets[0].data), [2.5, 3.5]);
assert.equal(people.hidden, true);
assert.ok(chart.updates >= 4);

console.log("Team composite chart #375: mode switching, orientation, initials and privacy contract OK");
