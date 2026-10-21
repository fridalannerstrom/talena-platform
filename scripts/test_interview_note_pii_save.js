"use strict";

// No browser, server, candidate data or external services required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/js/talena/interview-question-notes.js", "utf8");
assert.match(source, /Vi hittade möjliga personuppgifter/);
assert.match(source, /Possible personal data detected/);
assert.match(source, /piiWarning\.setAttribute\("role", "alert"\)/);
assert.match(source, /field\.setAttribute\("aria-describedby",/);

function classes() {
  return { add() {}, remove() {}, toggle() {} };
}

async function verifyBlockedSave(language) {
  const listeners = {};
  const warning = { hidden: true };
  const status = { textContent: "", classList: classes() };
  const button = {
    disabled: false,
    textContent: "Save",
    classList: classes(),
    hasAttribute() { return false; },
    closest() { return root; },
  };
  const root = {
    querySelector(selector) {
      if (selector.includes("pii-warning")) return warning;
      if (selector.includes("note-status")) return status;
      if (selector.includes("note-save")) return button;
      if (selector.includes("[data-interview-question-note]")) return field;
      return null;
    },
  };
  const attributes = {};
  const field = {
    value: "Anna Svensson och anna@example.se",
    dataset: {
      notesUrl: "/test/notes/",
      updateUrl: "/test/notes/update/",
      savedValue: "",
      questionSource: "personality",
      questionText: "Tell me about a situation.",
    },
    closest() { return root; },
    setAttribute(name, value) { attributes[name] = value; },
    removeAttribute(name) { delete attributes[name]; },
  };
  const fetchCalls = [];
  const document = {
    cookie: "csrftoken=token",
    documentElement: { lang: language },
    addEventListener(type, callback) { listeners[type] = callback; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
  };
  const context = {
    document,
    window: { addEventListener() {}, TalenaInterviewQuestionNotes: {} },
    Element: class {},
    MutationObserver: class { observe() {} },
    CustomEvent: class {},
    console,
    fetch: async (url, options) => {
      fetchCalls.push({ url, options });
      return {
        status: 422,
        ok: false,
        json: async () => ({ code: "personal_data_detected" }),
      };
    },
  };

  vm.runInNewContext(source, context, { filename: "interview-question-notes.js" });
  listeners.click({
    target: { closest(selector) {
      return selector === "[data-interview-question-note-save]" ? button : null;
    } },
  });

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(fetchCalls.length, 1);
  assert.equal(warning.hidden, false);
  assert.equal(attributes["aria-invalid"], "true");
  assert.equal(field.value, "Anna Svensson och anna@example.se");
  assert.equal(button.disabled, false, "allow the user to correct the note");

  field.value = "Beskriver samarbete med kollegor.";
  listeners.input({
    target: { closest(selector) {
      return selector === "[data-interview-question-note]" ? field : null;
    } },
  });
  assert.equal(warning.hidden, true);
  assert.equal(attributes["aria-invalid"], undefined);
}

(async () => {
  await verifyBlockedSave("sv");
  await verifyBlockedSave("en");
  console.log("Interview question note privacy warning smoke passed.");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
