/* Regression for account invitation bilingual form defaults (#454). */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const code = fs.readFileSync("static/js/talena/account-invite-language.js", "utf8");

const translations = {
  subject: { en: "Welcome to Talena", sv: "Välkommen till Talena" },
  message: {
    en: "You've received a Talena account, bringing assessment processes, results and AI-supported insights together in one clear workflow.",
    sv: "Du har blivit inbjuden till Talena, där du kan arbeta med testresultat, insikter och rekryteringsprojekt på ett och samma ställe.",
  },
};

function textField(defaults) {
  return {
    value: defaults.en,
    dataset: { inviteDefaultEn: defaults.en, inviteDefaultSv: defaults.sv },
    events: [],
    dispatchEvent(event) { this.events.push(event.type); },
  };
}

const subject = textField(translations.subject);
const message = textField(translations.message);
const form = {
  querySelector(selector) {
    if (selector === '[name="invite_subject"]') return subject;
    if (selector === '[name="invite_message"]') return message;
    return null;
  },
};
const select = {
  value: "en",
  closest(selector) { return selector === "form" ? form : null; },
  matches(selector) { return selector === 'select[name="invite_language"]'; },
};
const handlers = {};
const document = {
  readyState: "complete",
  addEventListener(type, callback) { handlers[type] = callback; },
  querySelectorAll(selector) {
    return selector === 'select[name="invite_language"]' ? [select] : [];
  },
};

class FakeEvent {
  constructor(type) { this.type = type; }
}

vm.runInNewContext(code, { document, Event: FakeEvent });

select.value = "sv";
handlers.change({ target: select });
assert.equal(subject.value, translations.subject.sv, "Subject switches to Swedish");
assert.equal(message.value, translations.message.sv, "Body switches to Swedish");

select.value = "en";
handlers.change({ target: select });
assert.equal(subject.value, translations.subject.en, "Subject switches back to English");
assert.equal(message.value, translations.message.en, "Body switches back to English");

// A personalised message is an intentional edit, so the language picker
// must not erase it when the admin switches email language.
message.value = "Personal greeting for the new user.";
select.value = "sv";
handlers.change({ target: select });
assert.equal(subject.value, translations.subject.sv, "Untouched subject translates");
assert.equal(message.value, "Personal greeting for the new user.", "Custom body preserved");

subject.value = "Your personal onboarding";
select.value = "en";
handlers.change({ target: select });
assert.equal(subject.value, "Your personal onboarding", "Custom subject preserved");
assert.equal(message.value, "Personal greeting for the new user.", "Custom body still preserved");
assert.ok(subject.events.includes("input") && message.events.includes("input"));

console.log("Account invitation bilingual subject and body sync: OK");
