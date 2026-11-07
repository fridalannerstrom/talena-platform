"use strict";
// #428: verify the one Personality AI badge has keyboard/touch help.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const source = fs.readFileSync("static/js/talena/candidate-ai-badges.js", "utf8");
const css = fs.readFileSync("static/css/talena/pages/candidate-eyebrows.css", "utf8");
const header = fs.readFileSync("templates/customer/processes/_process_header.html", "utf8");
const begin = source.indexOf("  let personalityHelpSequence = 0;");
const end = source.indexOf("  function removeLegacyKickers(root) {", begin);
assert.ok(begin > 0 && end > begin);
const names = new Set();
class FakeElement {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.attributes = {};
    this.classList = { add: (name) => names.add(name) };
  }
  appendChild(child) { child.parentElement = this; this.children.push(child); }
  querySelector(selector) {
    return selector.includes(".talena-ai-personality-help")
      ? this.children.find(child => child.className === "talena-ai-personality-help") || null
      : null;
  }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
}
const document = { createElement: name => new FakeElement(name) };
const attach = new Function("document", "isSwedish", "label",
  source.slice(begin, end) + "return attachPersonalityHelp;")(
    document, () => true, () => "AI-genererat"
  );
const row = new FakeElement("div");
const badge = new FakeElement("span");
row.appendChild(badge);
attach(badge, false);
assert.equal(row.children.length, 2, "Only one explanation should be appended");
assert.ok(names.has("talena-ai-title-row--personality-help"));
assert.equal(badge.tabIndex, 0);
assert.equal(badge.getAttribute("role"), "button");
assert.equal(badge.getAttribute("aria-expanded"), "false");
assert.equal(badge.getAttribute("aria-describedby"), row.children[1].id);
assert.ok(row.children[1].textContent.includes(
  "Denna text är AI-genererad och avsedd som stöd för förståelse och vidare samtal."
));
assert.ok(row.children[1].textContent.includes("Statiska testresultat"));
attach(badge, false);
assert.equal(row.children.length, 2, "Re-scan must reuse the same tooltip");
badge.listeners.click();
assert.equal(badge.getAttribute("aria-expanded"), "true", "Touch click opens help");
badge.listeners.keydown({ key: "Escape" });
assert.equal(badge.getAttribute("aria-expanded"), "false", "Escape closes help");
let prevented = false;
badge.listeners.keydown({ key: "Enter", preventDefault: () => { prevented = true; } });
assert.ok(prevented);
assert.equal(badge.getAttribute("aria-expanded"), "true", "Enter opens help");
badge.listeners.blur();
assert.equal(badge.getAttribute("aria-expanded"), "false", "Blur closes help");
attach(badge, true);
assert.ok(row.children[1].textContent.includes("redigerats manuellt"));
assert.ok(badge.getAttribute("aria-label").includes("AI-genererat"));
assert.ok(!badge.getAttribute("aria-label").includes("AI-assisterat"),
  "An edited AI text keeps the visible label AI-genererat");
for (const selector of [
  '.talena-ai-generated-badge:hover ~ .talena-ai-personality-help',
  '.talena-ai-generated-badge:focus-visible ~ .talena-ai-personality-help',
  '.talena-ai-generated-badge[data-help-open="true"] ~ .talena-ai-personality-help'
]) assert.ok(css.includes(selector), "Missing access path " + selector);
assert.ok(css.includes(".talena-ai-personality-help {"));
assert.ok(css.includes("@media print"));
assert.ok(header.includes("428-personality-help-v3"));
assert.ok(header.includes("428-tooltip-v1"));
console.log("Ticket #428: one Personality badge with accessible mouse, keyboard and touch help passed.");
