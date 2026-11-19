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

assert(js.includes("function buildCreateSetting()"));
assert(js.includes('data.automaticInvitationSetting = "true"') ||
       js.includes('row.dataset.automaticInvitationSetting = "true"'));
assert(js.includes('marker.name = "automatic_invitation_setting_present"'));
assert(js.includes('input.name = "automatic_invitation_enabled"'));
assert(js.includes('[data-wizard-automatic-invitation]'));
assert(js.includes("function mountSettingsSetting()"), "Existing edit-page mount must remain");
assert(js.includes("buildSetting({"), "Existing edit-page implementation must remain");

assert(css.includes("/* Unified final-step layout (2026-11-19)"));
assert(css.includes(".wizard-setting-row"));
assert(css.includes(".candidate-language-section"));

console.log("Customer project wizard final-step structure and settings contract: OK");
