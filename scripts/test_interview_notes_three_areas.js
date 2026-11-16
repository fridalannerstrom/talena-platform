"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
require("../static/js/talena/interview-note-areas.js");

const area = globalThis.TalenaInterviewNoteAreas;
assert.ok(area && typeof area.initialise === "function");

const original = {
  personality: "Kandidaten beskriver hur hen samarbetar.\nMed flera kollegor.",
  motivation: "Det ger energi att hitta en lösning och möta kunder.",
  skills: 'Jag jämförde numeriska data och drog en logisk slutsats. "Citat".',
};
const encoded = area.serialize(original);
assert.ok(encoded.includes("### Intervjuunderlag: Personlighet"));
assert.ok(encoded.includes("### Intervjuunderlag: Motivation"));
assert.ok(encoded.includes("### Intervjuunderlag: Färdighet"));
assert.deepEqual(area.parse(encoded), { sections: original, legacy: false });

const onlyMotivation = area.serialize({ motivation: "Glädje och utveckling." });
assert.deepEqual(area.parse(onlyMotivation), {
  sections: { personality: "", motivation: "Glädje och utveckling.", skills: "" },
  legacy: false,
});
assert.equal(area.serialize({}), "");
assert.deepEqual(area.parse(""), {
  sections: { personality: "", motivation: "", skills: "" }, legacy: false,
});

// Do not guess what older uncategorised evidence means, and never destroy it
// just because someone opens the candidate's page.
const legacyText = [
  "Färdighet:",
  "Numerisk: Kandidaten granskade siffror.",
  "Motivation",
  "Kandidaten berättade om energi på jobbet.",
  "Personlighet: Beskrev samarbete.",
].join("\n");
const legacy = area.parse(legacyText);
assert.equal(legacy.sections.personality, legacyText);
assert.equal(legacy.sections.motivation, "");
assert.equal(legacy.sections.skills, "");
assert.equal(legacy.legacy, true);

// Test the actual DOM wiring, including the input event consumed by the
// already-installed original status/save scripts.
const fields = {};
for (const key of ["personality", "motivation", "skills"]) {
  fields[key] = {
    value: "",
    _listeners: {},
    addEventListener(type, callback) { this._listeners[type] = callback; },
    input(value) { this.value = value; this._listeners.input(); },
  };
}
const hint = { hidden: true };
const panel = {
  dataset: {},
  querySelector(selector) {
    if (selector === "[data-interview-notes-legacy-help]") return hint;
    const match = selector.match(/^\[data-interview-notes-area="([^"]+)"\]$/);
    return match ? fields[match[1]] : null;
  },
};
let inputEvents = 0;
const combined = {
  value: legacyText,
  dispatchEvent(event) { if (event.type === "input") inputEvents++; },
};
const root = {
  querySelector(selector) {
    return selector === "[data-interview-notes-areas]" ? panel
      : selector === "[data-interview-notes-input]" ? combined
      : null;
  },
};
area.initialise(root);
assert.equal(combined.value, legacyText, "Opening old notes must not rewrite AI input");
assert.equal(inputEvents, 0, "Opening notes must not flag reports as changed");
assert.equal(fields.personality.value, legacyText);
assert.equal(hint.hidden, false);
area.initialise(root); // idempotent for dynamically mounted pages
fields.motivation.input("Söker variation.");
assert.equal(inputEvents, 1, "One editor input creates one native input event");
assert.ok(combined.value.startsWith(legacyText));
assert.ok(!combined.value.includes("### Intervjuunderlag: Personlighet"),
  "Editing other areas must not reclassify older notes");
assert.equal(area.parse(combined.value).sections.personality, legacyText);
assert.equal(area.parse(combined.value).sections.motivation, "Söker variation.");
assert.equal(area.parse(combined.value).sections.skills, "");
assert.equal(area.parse(combined.value).legacy, true);

// Source of truth stays the existing interview_notes field; no new endpoint,
// model schema, AI prompt or report generator is necessary.
const template = fs.readFileSync(
  "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html", "utf8"
);
const parent = fs.readFileSync("templates/customer/processes/process_base.html", "utf8");
for (const key of ["personality", "motivation", "skills"]) {
  assert.ok(template.includes('data-interview-notes-area="' + key + '"'));
}
assert.ok(template.includes('data-interview-notes-input'));
assert.ok(parent.includes("TalenaInterviewNoteAreas?.initialise(root)"));
assert.ok(parent.includes("interview_notes: input.value"));
assert.match(parent, /interview_notes:\s*notesInput\.value/);
console.log("Interview notes three-area UI, legacy data and unchanged AI input contract: OK");
