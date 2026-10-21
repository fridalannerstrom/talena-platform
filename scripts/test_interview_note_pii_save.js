"use strict";

// JS smoke: saving succeeds regardless of PII; the server-confirmed boolean
// controls a calm notice, never an error or a second request.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("static/js/talena/interview-question-notes.js", "utf8");
const css = fs.readFileSync("static/css/talena/pages/interview-question-notes.css", "utf8");
assert.match(source, /Vi hjälper dig att skydda personuppgifter/);
assert.match(source, /We help you protect personal data/);
assert.match(source, /Din anteckning är sparad! Talena försöker maskera namn och kontaktuppgifter/);
assert.match(source, /Your note is saved! Talena attempts to mask names and contact details/);
assert.match(source, /shieldIcon\.dataset\.feather = "shield"/);
assert.match(source, /noticeIcon\.setAttribute\("aria-hidden", "true"\)/);
assert.match(source, /piiNotice\.append\(noticeIcon, noticeCopy\)/);
assert.match(css, /interview-question-note__pii-notice-icon svg/);
assert.match(css, /\.interview-question-note__pii-notice \{\s*display: flex;/);
assert.doesNotMatch(source, /masking is guaranteed|maskerar alltid allt/i);
assert.match(source, /piiNotice\.setAttribute\("role", "status"\)/);
assert.match(source, /setPiiSaveInfo\(field, payload.possible_personal_data === true\)/);
assert.match(css, /interview-question-note__pii-notice-title/);
assert.match(css, /interview-question-note__pii-notice-body/);
assert.doesNotMatch(source, /personal_data_detected/);

function classes() {
  return { add() {}, remove() {}, toggle() {} };
}

async function verifyNonBlockingSave(language, containsPii) {
  const listeners = {};
  const notice = { hidden: true };
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
      if (selector.includes("pii-notice")) return notice;
      if (selector.includes("note-status")) return status;
      if (selector.includes("note-save")) return button;
      if (selector.includes("[data-interview-question-note]")) return field;
      return null;
    },
  };
  const original = containsPii ? "Anna Exempelson, name@example.org" : "Led a productive meeting";
  const field = {
    value: original,
    dataset: {
      notesUrl: "/test/notes/",
      updateUrl: "/test/notes/update/",
      savedValue: "",
      questionSource: "personality",
      questionText: "Tell me about a situation.",
    },
    closest() { return root; },
    setAttribute(name, value) { this[name] = value; },
    removeAttribute(name) { delete this[name]; },
  };
  const fetchCalls = [];
  const document = {
    cookie: "csrftoken=token",
    documentElement: { lang: language },
    addEventListener(type, callback) { listeners[type] = callback; },
    dispatchEvent() {},
    querySelectorAll(selector) {
      if (selector === "[data-interview-question-note]") return [field];
      return [];
    },
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
        status: 200,
        ok: true,
        json: async () => ({
          ok: true,
          note: { note: original },
          possible_personal_data: containsPii,
          post_interview_status: "outdated",
        }),
      };
    },
  };

  vm.runInNewContext(source, context, { filename: "interview-question-notes.js" });
  listeners.click({
    target: { closest(selector) {
      return selector === "[data-interview-question-note-save]" ? button : null;
    } },
  });
  await new Promise(resolve => setTimeout(resolve, 0));

  assert.equal(fetchCalls.length, 1);
  const submitted = JSON.parse(fetchCalls[0].options.body);
  assert.equal(submitted.note, original, "send the note unchanged");
  assert.equal(field.dataset.savedValue, original, "successful save marks field saved");
  assert.equal(button.disabled, true, "successful save resets dirty state");
  assert.equal(status.textContent, language === "sv" ? "Sparat" : "Saved");
  assert.equal(notice.hidden, !containsPii);
  assert.equal(field["aria-invalid"], undefined, "personal data is informational");

  field.value = "Reflected on cooperation with colleagues";
  listeners.input({
    target: { closest(selector) {
      return selector === "[data-interview-question-note]" ? field : null;
    } },
  });
  assert.equal(notice.hidden, true, "changing text clears stale notice");
  assert.equal(button.disabled, false, "allow another save");
}

(async () => {
  for (const lang of ["sv", "en"]) {
    await verifyNonBlockingSave(lang, true);
    await verifyNonBlockingSave(lang, false);
  }
  console.log("Interview note non-blocking privacy advisory smoke passed.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
