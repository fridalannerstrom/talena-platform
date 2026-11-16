/* #353: Browser-free click regression for read-only Personality navigation. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const script = fs.readFileSync("static/js/talena/admin-candidate-mirror-353.js", "utf8");
const customer = fs.readFileSync(
  "templates/customer/processes/partials/candidate_insights/personality/_results.html",
  "utf8"
);
const names = ["detailed", "quick", "descriptions", "response-styles"];

for (const name of names) {
  assert.ok(customer.includes('data-personality-view-tab="' + name + '"'));
  assert.ok(customer.includes('data-personality-view-panel="' + name + '"'));
}

const events = new Map();
const document = {
  readyState: "loading",
  addEventListener(name, cb) { events.set(name, cb); },
  querySelectorAll(selector) {
    return selector === "[data-admin-candidate-mirror]" ? [mirror] : [];
  },
  getElementById() { return null; },
};
function node(initial = {}) {
  const classes = new Set();
  const attrs = new Map(Object.entries(initial.attrs || {}));
  return {
    dataset: initial.dataset || {},
    hidden: Boolean(initial.hidden),
    disabled: false,
    tabIndex: 0,
    classList: {
      toggle(name, on) {
        if (on) classes.add(name);
        else classes.delete(name);
      },
      contains(name) { return classes.has(name); },
    },
    setAttribute(name, value) { attrs.set(name, String(value)); },
    getAttribute(name) { return attrs.get(name) || null; },
    matches(selector) {
      if (this.dataset.personalityViewTab) {
        return selector.includes("[data-personality-view-tab]");
      }
      return false;
    },
    closest(selector) {
      if (selector === "[data-personality-profile-root]") return root;
      if (selector === "[data-admin-candidate-mirror]") return mirror;
      return null;
    },
  };
}
const tabs = names.map(name => node({
  dataset: { personalityViewTab: name },
  attrs: { "aria-selected": String(name === "detailed") },
}));
const panels = names.map(name => node({
  dataset: { personalityViewPanel: name },
  hidden: name !== "detailed",
}));
const detailOnly = node();
const generate = node();
const root = {
  querySelectorAll(selector) {
    if (selector === "[data-personality-view-tab]") return tabs;
    if (selector === "[data-personality-view-panel]") return panels;
    if (selector === "[data-personality-detailed-only]") return [detailOnly];
    return [];
  },
};
const mirror = {
  dataset: {},
  matches() { return false; },
  querySelectorAll(selector) { return selector === "button" ? [...tabs, generate] : []; },
};
vm.runInNewContext(script, {
  window: {}, document,
  MutationObserver: class {},
  console,
});
assert.ok(events.has("DOMContentLoaded"));
assert.ok(events.has("click"));
events.get("DOMContentLoaded")();
for (const tab of tabs) {
  assert.equal(tab.disabled, false, "read-only navigation was disabled");
  assert.notEqual(tab.getAttribute("aria-disabled"), "true");
}
assert.equal(generate.disabled, true, "mutation control must remain blocked");

function click(target, expectedBlocked) {
  let prevented = false;
  let stopped = false;
  const event = {
    target: {
      closest(selector) {
        if (selector === "[data-admin-candidate-mirror]") return mirror;
        if (selector.includes("button, a")) return target;
        return null;
      },
    },
    preventDefault() { prevented = true; },
    stopImmediatePropagation() { stopped = true; },
  };
  events.get("click")(event);
  assert.equal(prevented, expectedBlocked);
  assert.equal(stopped, expectedBlocked);
}
for (const name of ["quick", "descriptions", "response-styles", "detailed"]) {
  click(tabs[names.indexOf(name)], false);
  for (let i = 0; i < names.length; i++) {
    const active = names[i] === name;
    assert.equal(tabs[i].getAttribute("aria-selected"), String(active));
    assert.equal(tabs[i].classList.contains("is-active"), active);
    assert.equal(panels[i].hidden, !active);
    assert.equal(tabs[i].tabIndex, active ? 0 : -1);
  }
  assert.equal(detailOnly.hidden, name !== "detailed");
}
click(generate, true);
console.log("#353: all four Personality views navigate in admin; mutation blocked");
