/* Lightweight browser-behaviour regression for role context AI-save spinner.
 * Uses only built-in Node APIs; no network/DOM dependencies.
 */
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const js = fs.readFileSync("static/js/talena/role-context-saving.js", "utf8");
const html = fs.readFileSync("templates/customer/processes/process_role_context.html", "utf8");
const css = fs.readFileSync("static/css/talena/pages/process-context.css", "utf8");

for (const required of [
  "data-role-context-form",
  "data-role-context-saving-overlay",
  "data-role-context-saving-card",
  "data-role-context-saving-hint",
  "data-role-context-saving-long-hint",
  "Talena väljer personlighetsdrag…",
  "Talena is selecting personality traits…",
  "åtta rekommenderade",
  "eight recommended",
  "js/talena/role-context-saving.js",
  "?v=20261123-trait-progress-v1",
]) assert.ok(html.includes(required), "Missing template element: " + required);
for (const required of [
  ".role-context-saving-overlay[hidden]",
  ".role-context-saving-orb__ring",
  "@keyframes role-trait-ring",
  "@keyframes role-trait-progress",
  "prefers-reduced-motion: reduce",
]) assert.ok(css.includes(required), "Missing loading UI CSS: " + required);
assert.ok(!js.includes("fetch("), "Never issue a separate AI request from the browser.");
assert.ok(!js.includes("requestSubmit("), "Never submit the form twice.");
assert.ok(!js.includes("event.preventDefault(); // Do not"), "Do not block the original save.");

function setup(original) {
  const saved = original;
  const callbacks = {};
  const windowCallbacks = {};
  const timers = [];
  const card = {focused: false, focus() { this.focused = true; }};
  const hint = {hidden: false};
  const longHint = {hidden: true};
  const overlay = {
    hidden: true,
    querySelector(selector) {
      const map = {
        "[data-role-context-saving-card]": card,
        "[data-role-context-saving-hint]": hint,
        "[data-role-context-saving-long-hint]": longHint,
      };
      return map[selector] || null;
    },
  };
  const field = {value: saved, defaultValue: saved};
  const form = {
    dataset: {},
    attributes: {},
    selectedTraits: 8,
    querySelector(selector) {
      return selector === 'textarea[name="context_text"]' ? field : null;
    },
    querySelectorAll(selector) {
      assert.equal(selector, 'input[name="personality_question_traits"]:checked');
      return Array(this.selectedTraits).fill({});
    },
    addEventListener(type, callback) { callbacks[type] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
  };
  const window = {
    addEventListener(type, callback) { windowCallbacks[type] = callback; },
    setTimeout(callback, delay) {
      assert.equal(delay, 18000);
      timers.push(callback);
      return timers.length;
    },
  };
  const document = {
    readyState: "complete",
    querySelector(selector) {
      return {
        "[data-role-context-form]": form,
        "[data-role-context-saving-overlay]": overlay,
      }[selector] || null;
    },
  };
  vm.runInNewContext(js, {document, window, clearTimeout() {}}, {filename: "role-context-saving.js"});
  return {
    field, form, overlay, card, hint, longHint, timers,
    submit(value, submitterName = "", selected = 8) {
      field.value = value;
      form.selectedTraits = selected;
      const event = {
        prevented: false,
        submitter: {name: submitterName},
        preventDefault() { this.prevented = true; },
      };
      callbacks.submit(event);
      return event;
    },
    pageshow() { windowCallbacks.pageshow(); },
  };
}

{
  const ui = setup("Original recruiter role");
  const event = ui.submit("Original recruiter role");
  assert.equal(event.prevented, false);
  assert.equal(ui.overlay.hidden, true, "Unchanged save should be immediate.");
}
{
  const ui = setup("Original recruiter role");
  assert.equal(ui.submit("Updated recruiter role").prevented, false);
  assert.equal(ui.overlay.hidden, false, "Changed role must show progress.");
  assert.equal(ui.form.attributes["aria-busy"], "true");
  assert.equal(ui.card.focused, true);
  assert.equal(ui.timers.length, 1);
  ui.timers[0]();
  assert.equal(ui.hint.hidden, true);
  assert.equal(ui.longHint.hidden, false);
  assert.equal(ui.submit("Updated recruiter role").prevented, true,
    "A second click must not trigger a second AI request.");
  ui.pageshow();
  assert.equal(ui.overlay.hidden, true, "Restore from history must dismiss overlay.");
  assert.equal(ui.form.attributes["aria-busy"], undefined);
}
{
  const ui = setup("Existing role");
  ui.submit("Changed role", "save_personality_traits", 8);
  assert.equal(ui.overlay.hidden, true,
    "Manually selecting eight traits must not show the AI overlay.");
}
{
  const ui = setup("Existing role");
  ui.submit("Existing role", "save_personality_traits", 0);
  assert.equal(ui.overlay.hidden, false,
    "Switching to Talena's automatic eight should display loading.");
}
{
  const ui = setup("");
  ui.submit("");
  assert.equal(ui.overlay.hidden, true,
    "Empty context does not generate eight new traits.");
}

console.log("Role-context AI selection progress UI checks passed.");
