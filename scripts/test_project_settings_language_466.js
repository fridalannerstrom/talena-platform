"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const rootDir = path.resolve(__dirname, "..");
const template = fs.readFileSync(
  path.join(rootDir, "templates/customer/processes/process_edit.html"),
  "utf8"
);
const script = fs.readFileSync(
  path.join(rootDir, "static/js/talena/process-settings.js"),
  "utf8"
);

// Both fields must have source copy for both project candidate languages.
const expectedCopy = [
  "Kandidatspråk",
  "Candidate language",
  "Välj språk för kandidatens inbjudningar och tester.",
  "Choose the language used for candidate invitations and assessments.",
  "Inbjudan och tester på svenska",
  "Invitation and assessments in Swedish",
  "Inbjudan och tester på engelska",
  "Invitation and assessments in English",
  "Mejla projektägaren när en kandidat slutfört alla tester",
  "Email the project creator when a candidate completes all tests",
  "Den som skapade projektet får ett mejl",
  "The project creator receives an email",
];
for (const snippet of expectedCopy) {
  assert.ok(template.includes(snippet), `Missing translation: ${snippet}`);
}
assert.ok(template.includes('data-project-language="sv"'));
assert.ok(template.includes('data-project-language="en"'));
assert.ok(template.includes('{% if form.candidate_language.value == "en" %}hidden{% endif %}'));
assert.ok(template.includes('{% if form.candidate_language.value != "en" %}hidden{% endif %}'));
assert.ok(!template.includes('LANGUAGE_CODE|slice:":2"'), "UI locale should not override project selection");

// Simulate the project language radios and the copies on the settings page.
const listeners = {};
const radios = [
  {
    value: "sv",
    checked: true,
    addEventListener(name, fn) { listeners[`sv:${name}`] = fn; },
  },
  {
    value: "en",
    checked: false,
    addEventListener(name, fn) { listeners[`en:${name}`] = fn; },
  },
];
const copies = [
  { dataset: { projectLanguage: "sv" }, hidden: true },
  { dataset: { projectLanguage: "en" }, hidden: false },
  { dataset: { projectLanguage: "sv" }, hidden: true },
  { dataset: { projectLanguage: "en" }, hidden: false },
];
const settingsRoot = {
  dataset: { templateLocked: "false" },
  querySelector(selector) {
    if (selector === 'input[name="candidate_language"]:checked') {
      return radios.find((radio) => radio.checked) || null;
    }
    return null;
  },
  querySelectorAll(selector) {
    if (selector === 'input[name="candidate_language"]') return radios;
    if (selector === "[data-project-language]") return copies;
    return [];
  },
};
const document = {
  readyState: "complete",
  querySelector(selector) {
    return selector === ".process-settings-page" ? settingsRoot : null;
  },
};

vm.runInNewContext(script, { document, window: {} });
assert.deepEqual(copies.map((copy) => copy.hidden), [false, true, false, true]);
radios[0].checked = false;
radios[1].checked = true;
listeners["en:change"]();
assert.deepEqual(copies.map((copy) => copy.hidden), [true, false, true, false]);
radios[0].checked = true;
radios[1].checked = false;
listeners["sv:change"]();
assert.deepEqual(copies.map((copy) => copy.hidden), [false, true, false, true]);

console.log("Project settings language follows the selected candidate language (SV/EN).");
