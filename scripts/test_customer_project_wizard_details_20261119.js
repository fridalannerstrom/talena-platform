"use strict";

// Static UI contract: final-step hierarchy and the auto-invitation POST bridge.
// Run with: node scripts/test_customer_project_wizard_details_20261119.js
const fs = require("node:fs");
const assert = require("node:assert/strict");

const html = fs.readFileSync(
  "templates/customer/processes/process_create_v2.html", "utf8",
);
const js = fs.readFileSync(
  "static/js/talena/automatic-invitation-setting.js", "utf8",
);
const css = fs.readFileSync(
  "static/css/talena/pages/process-create.css", "utf8",
);

const finalStepStart = html.indexOf('<!-- STEP 3: Project details and shared, compact settings -->');
assert(finalStepStart !== -1, "Missing final wizard step");
const finalStep = html.slice(finalStepStart, html.indexOf("</section>\n\n    </div>\n  </form>", finalStepStart) + 10);
assert(finalStep.includes("wizard-details-basics"), "Basic details section missing");
assert(finalStep.includes("wizard-details-language"), "Candidate language section missing");
assert(finalStep.includes("wizard-details-settings"), "Project settings section missing");
assert(
  finalStep.indexOf("wizard-details-basics") <
  finalStep.indexOf("wizard-details-language") &&
  finalStep.indexOf("wizard-details-language") <
  finalStep.indexOf("wizard-details-settings"),
  "Sections are not in expected order",
);
assert(finalStep.includes('id="processNameInput"'));
assert(finalStep.includes('id="processLabelsInput"'));
assert(!finalStep.includes('class="col-12 col-lg-7"'), "Project name should be full width");
assert(!finalStep.includes('class="col-12 col-lg-5"'), "Labels should be full width");
assert.equal(
  (finalStep.match(/class="col-12"/g) || []).length,
  2,
  "Project name and labels must occupy separate full-width rows",
);
assert(finalStep.includes('name="candidate_language"'));
assert(finalStep.includes("form.candidate_results_enabled"));
assert(finalStep.includes('data-wizard-automatic-invitation'));
for (const value of ["default", "on", "off"]) {
  assert(finalStep.includes('name="integrity_guard_visibility" value="' + value + '"'));
}
assert(!finalStep.includes("Övervakningen hos Sova"));
assert(!finalStep.includes("Monitoring in Sova"));
assert(!finalStep.includes("candidate-results-setting mt-4 p-3 border rounded-3"));
assert(!finalStep.includes("wizard-ig-setting mt-4"));
assert(finalStep.indexOf("wizardIgTitle") < finalStep.lastIndexOf('type="submit"'));

assert(js.includes("function buildCreateSetting({ checked = false } = {})"));
assert(js.includes('data.automaticInvitationSetting = "true"') ||
       js.includes('row.dataset.automaticInvitationSetting = "true"'));
assert(js.includes('marker.name = "automatic_invitation_setting_present"'));
assert(js.includes('input.name = "automatic_invitation_enabled"'));
assert(js.includes('[data-wizard-automatic-invitation]'));
assert(js.includes("function mountSettingsSetting()"), "Existing edit-page mount must remain");
assert(js.includes("buildSetting({"), "Existing edit-page implementation must remain");

assert(css.includes("/* Unified final-step layout (2026-11-19)"));
const modal = html.slice(html.indexOf('id="wizardIgInfoModal"'));
assert(finalStep.includes('type="button" class="wizard-ig-explain-link"'));
assert(finalStep.includes('data-bs-toggle="modal" data-bs-target="#wizardIgInfoModal"'));
assert(finalStep.includes('Vad är Integrity Guard?'));
assert(finalStep.includes('What is Integrity Guard?'));
assert(html.indexOf('id="wizardIgInfoModal"') > html.indexOf('</form>'),
  "Info dialog must not be nested in the project form");
assert(modal.includes('aria-labelledby="wizardIgInfoTitle"'));
assert(modal.includes('aria-describedby="wizardIgInfoIntro"'));
assert(modal.includes('data-bs-dismiss="modal"'));
for (const phrase of [
  "En avvikelse är inte bevis på fusk",
  "IP-adresser",
  "Använda enheter",
  "Flikar och webbläsare",
  "Svarsmönster",
  "utvecklas och valideras fortfarande",
  "A flag is not proof of cheating",
]) {
  assert(modal.includes(phrase), "Missing grounded explanation: " + phrase);
}
assert(css.includes(".wizard-ig-explain-link"));
assert(css.includes(".wizard-ig-info-modal .wizard-ig-modal-checks"));

assert.equal(
  (finalStep.match(/class="wizard-ig-option-label"/g) || []).length, 3,
  "Three Integrity Guard choices must have pill labels",
);
assert.equal(
  (finalStep.match(/class="fa-solid fa-check wizard-ig-choice-check"/g) || []).length, 3,
  "Each Integrity Guard choice must show a check when selected",
);
assert(css.includes(".wizard-ig-option input:checked + .wizard-ig-option-label") ||
       css.includes(".wizard-ig-option input:checked + .wizard-ig-option-label"),
       "Checked choice must receive selected styling");
assert(css.includes(".wizard-ig-choice-check"), "Selected checkmark style missing");
assert(css.includes("height: 48px !important;"), "Account, name and labels must have equal height");
assert(css.includes(".wizard-details-basics .wizard-account-field select.form-select"),
       "Account select equal-height rule missing");
assert(css.includes(".wizard-details-basics #processNameInput.form-control"),
       "Project name equal-height rule missing");
assert(css.includes(".wizard-details-basics #processLabelsInput.form-control"),
       "Labels equal-height rule missing");
const igLinkStyle = css.slice(css.lastIndexOf("#processCreateWizardForm .wizard-ig-explain-link {"));
assert(igLinkStyle.includes("margin: 0;"), "Integrity Guard help link must have no left margin");
assert(!igLinkStyle.includes("margin: 0 0 0 0.3rem;"), "Legacy left margin must be removed");

assert(css.includes(".wizard-setting-row"));
assert(css.includes(".candidate-language-section"));

assert(finalStep.includes('class="wizard-details-grid"'), "Two-column layout wrapper missing");
assert(finalStep.includes('class="wizard-details-main"'), "Main details column missing");
assert(finalStep.includes('class="wizard-details-aside"'), "Right-hand settings card missing");
assert(finalStep.indexOf('class="wizard-details-main"') < finalStep.indexOf('class="wizard-details-aside"'));
assert(finalStep.indexOf('class="wizard-details-aside"') < finalStep.indexOf('wizardSettingsHeading'));
assert(finalStep.indexOf('wizardLanguageHeading') < finalStep.indexOf('class="wizard-details-aside"'));
assert(finalStep.includes('data-initial-enabled='), "Automatic invite selection must survive form errors");
assert(css.includes("grid-template-columns: minmax(0, 1.7fr) minmax(330px, 0.95fr)"));
assert(css.includes("@media (max-width: 1099.98px)"), "Settings must stack on narrow screens");
assert(css.includes("appearance: none !important;"), "Native checkbox artwork must be disabled");
assert(css.includes("background-image: none !important;"), "Bootstrap switch graphic must be removed");
assert(css.includes('input[type="checkbox"].form-check-input:checked::before'), "Custom thumb must move when toggled");

const vm = require("node:vm");

function mountCreateSwitch(initialEnabled) {
  const root = {
    children: [],
    dataset: {},
    append(...children) { this.children.push(...children); },
    appendChild(child) { this.children.push(child); },
  };
  const anchor = {
    children: [],
    dataset: { initialEnabled },
    appendChild(child) { this.children.push(child); },
  };
  const form = {
    querySelector(selector) {
      if (selector === "[data-wizard-automatic-invitation]") return anchor;
      if (selector === "[data-automatic-invitation-setting]") return anchor.children[0] || null;
      return null;
    },
  };
  const document = {
    readyState: "complete",
    documentElement: { lang: "sv" },
    createElement() {
      return {
        dataset: {},
        children: [],
        append(...items) { this.children.push(...items); },
        appendChild(item) { this.children.push(item); },
      };
    },
    querySelector(selector) {
      if (selector === "#processCreateWizardForm") return form;
      return null;
    },
  };
  vm.runInNewContext(js, { document, console }, { timeout: 3000 });
  assert.equal(anchor.children.length, 1, "Only one auto-invite control may be mounted");
  const row = anchor.children[0];
  const find = (node, name) => {
    if (node.name === name) return node;
    for (const child of node.children || []) {
      const match = find(child, name);
      if (match) return match;
    }
    return null;
  };
  const checkbox = find(row, "automatic_invitation_enabled");
  assert(checkbox, "Auto-invitation checkbox missing");
  assert.equal(checkbox.role, "switch");
  assert.equal(checkbox.checked, initialEnabled === "true");
  assert(find(row, "automatic_invitation_setting_present"), "POST presence marker missing");
  return checkbox;
}

assert.equal(mountCreateSwitch("true").checked, true, "Previous ON choice should be retained");
assert.equal(mountCreateSwitch("false").checked, false, "Previous OFF choice should be retained");

console.log("Customer project wizard layout, switches and persistence contract: OK");
