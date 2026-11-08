// #375: exercise the real SVG wheel with mock DOM nodes and check privacy.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/js/talena/team-preference-wheel.js", "utf8");
const pages = fs.readFileSync("static/js/talena/team-pages.js", "utf8");
const template = fs.readFileSync("templates/customer/teams/team_detail.html", "utf8");
const backend = fs.readFileSync("apps/teams/team_report_views.py", "utf8");
const css = fs.readFileSync("static/css/talena/pages/team-polish.css", "utf8");
const pdf = fs.readFileSync("static/js/talena/team-report-export.js", "utf8");

assert.ok(!template.includes('id="teamStyleAverageChart"'), "old radar must be removed");
assert.ok(template.includes('id="teamStylePreferenceWheel"'), "SVG wheel root missing");
assert.ok(template.includes('team-style-wheel-people'), "wheel needs authorised server data");
assert.ok(template.includes("team-preference-wheel.js"), "wheel JS asset is not loaded");
assert.ok(template.includes('data-team-chart-person-details'), "accessible full list missing");
assert.ok(template.includes('data-team-wheel-person'), "anonymity must mask SVG identities");
assert.ok(css.includes("team-composite-wheel-swatch--most"));
assert.ok(css.includes("team-composite-wheel-swatch--least"));
assert.ok(!pages.includes("initTeamStyleChart()"), "composite radar must not initialise");
assert.ok(pages.includes('getElementById("teamStylePreferenceWheel")'),
  "team guidance should still find the composite chart");
assert.ok(backend.includes('"chart_min_values"'), "numeric extrema must remain available");
assert.ok(backend.includes('"preference_wheel_rows"'), "member preferences must come from backend");
assert.ok(template.includes('team_style_stats.preference_wheel_rows'), "template should not show group extrema as member preferences");
assert.ok(pdf.includes("[data-team-wheel-person]"), "anonymous PDF must strip SVG initials");
assert.ok(pdf.includes("[data-team-chart-person-details]"),
  "anonymous PDF must exclude the full person list");

class Element {
  constructor(tag) {
    this.tag = tag;
    this.attrs = {};
    this.children = [];
    this.textContent = "";
    this.classList = { toggle() {} };
  }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key] || null; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  closest() { return this.section || null; }
}

const styles = ["Catalyst", "Director", "Energiser", "Architect",
  "Harmoniser", "Analyst", "Auditor", "Connector"];
const people = styles.map((style, index) => ({
  style,
  max: 4.5,
  min: 1.7,
  most: [{ name: "Anna Exempel", initials: "AE" },
    { name: "Bertil Exempel", initials: "BE" }],
  least: [{ name: "Cecilia Exempel", initials: "CE" }]
}));
people[0].most = Array.from({ length: 12 }, (_, i) => ({
  name: "Medlem " + i, initials: "M" + i
}));
const json = {
  "team-style-wheel-people": people,
  "team-style-chart-labels": styles
};
const buttons = ["both", "most", "least"].map(mode => ({
  dataset: { teamWheelMode: mode },
  attrs: {},
  classList: { toggle() {} },
  setAttribute(name, val) { this.attrs[name] = val; },
  addEventListener(name, fn) { this[name] = fn; }
}));
const section = { querySelectorAll: () => buttons };
const root = new Element("div");
root.dataset = {
  membersCount: "12", wheelLabel: "Teamets cirkulära preferenskarta",
  wheelMemberLabel: "med resultat", wheelOverflowLabel: "Se listan nedanför"
};
root.section = section;
const document = {
  readyState: "complete",
  documentElement: { lang: "sv" },
  getElementById(id) {
    if (id === "teamStylePreferenceWheel") return root;
    return Object.prototype.hasOwnProperty.call(json, id)
      ? { textContent: JSON.stringify(json[id]) } : null;
  },
  createElementNS(ns, tag) {
    assert.equal(ns, "http://www.w3.org/2000/svg");
    return new Element(tag);
  }
};

vm.runInNewContext(source, { document, console }, { timeout: 1200 });

function elements(parent, predicate) {
  const all = [];
  function visit(node) {
    if (predicate(node)) all.push(node);
    (node.children || []).forEach(visit);
  }
  visit(parent);
  return all;
}
assert.equal(root.dataset.wheelReady, "true");
assert.equal(root.children.length, 1);
const svg = root.children[0];
assert.equal(svg.tag, "svg");
assert.equal(svg.attrs.viewBox, "0 0 900 890");
assert.equal(svg.attrs.role, "img");
const sectors = elements(svg, n => n.tag === "path" && !!n.attrs["data-team-wheel-sector"]);
assert.equal(sectors.length, 16, "eight wedges per ring");
assert.deepEqual(sectors.filter(n => n.attrs["data-wheel-preference"] === "most")
  .map(n => n.attrs["data-team-wheel-sector"]), styles);
const badges = elements(svg, n => n.attrs["data-team-wheel-person"] !== undefined);
assert.ok(badges.length > 15, "member initials must be inside wheel sectors");
assert.ok(badges.some(n => elements(n, x => x.tag === "text" && x.textContent === "AE").length));
assert.ok(elements(svg, n => n.tag === "text" && n.textContent === "+7").length,
  "overflow should be summarised, with all names available below");
const rings = elements(svg, n => !!n.attrs["data-team-wheel-ring"]);
const outer = rings.find(n => n.attrs["data-team-wheel-ring"] === "most");
const inner = rings.find(n => n.attrs["data-team-wheel-ring"] === "least");
assert.equal(outer.attrs.visibility, "visible");
assert.equal(inner.attrs.visibility, "visible");

buttons[1].click();
assert.equal(root.dataset.wheelMode, "most");
assert.equal(outer.attrs.visibility, "visible");
assert.equal(inner.attrs.visibility, "hidden");
assert.equal(buttons[1].attrs["aria-pressed"], "true");
buttons[2].click();
assert.equal(root.dataset.wheelMode, "least");
assert.equal(outer.attrs.visibility, "hidden");
assert.equal(inner.attrs.visibility, "visible");
buttons[0].click();
assert.equal(outer.attrs.visibility, "visible");
assert.equal(inner.attrs.visibility, "visible");

// The complete source list can contain names, but only when allowed.
// Anonymous export must remove both visible and hidden identity-bearing DOM.
assert.ok(pdf.includes('"[data-team-chart-person-details], [data-team-wheel-person], .team-wheel-overflow"'));
console.log("Team wheel #375: sectors, in-wheel initials, modes and privacy contract OK");
