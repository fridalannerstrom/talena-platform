"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const tabs = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const copy = fs.readFileSync("static/js/talena/candidate-eyebrows.js", "utf8");
const view = fs.readFileSync("templates/customer/processes/partials/candidate_insights/tabs/_final_output.html", "utf8");
const shell = fs.readFileSync("templates/customer/core/layouts/customer_base.html", "utf8");
const header = fs.readFileSync("templates/customer/processes/_process_header.html", "utf8");
const page = fs.readFileSync("templates/customer/processes/process_base.html", "utf8");
const evidenceAvailability = fs.readFileSync("static/js/talena/post-interview-evidence-availability.js", "utf8");
const personalitySubtabs = fs.readFileSync("templates/customer/processes/partials/candidate_insights/tabs/_personality.html", "utf8");
const personalityResults = fs.readFileSync("templates/customer/processes/partials/candidate_insights/personality/_results.html", "utf8");
const sharedAssessmentStyles = fs.readFileSync("static/css/talena/pages/candidate-assessments.css", "utf8");
const reportTabStyles = fs.readFileSync("static/css/talena/pages/candidate-insight-tabs.css", "utf8");
const teamReportsTabs = fs.readFileSync("templates/customer/processes/partials/candidate_insights/tabs/_reports.html", "utf8");

// Two primary tabs: Evidence and Reports. The existing four report keys
// are nested rather than rewritten, preserving PDF, URL and refresh behavior.
for (const snippet of [
  'const keys = ["evidence", "overview", "interview", "explore", "managerReport"]',
  'const reportKeys = keys.filter((key) => key !== "evidence")',
  'primaryNav.appendChild(evidenceButton)',
  'primaryNav.appendChild(reportsButton)',
  'reportKeys.forEach((key) => {',
  'reportNav.appendChild(button)',
  'reportPanels.appendChild(tabPanel)',
  'reportsArea.append(reportsHeader, reportStatus, reportNavWrapper, reportPanels)',
  'tabs.append(journey, navSection, tabPanels)',
]) assert.ok(tabs.includes(snippet), "Two-level tab contract missing: " + snippet);

// A new candidate cannot access reports through tabs or a stale URL.
// Completed reports default to Helhetsbild/Overall picture after compilation.
for (const snippet of [
  'if (!hasCompiledPostInterviewResult) {\n      reportsButton.disabled = true',
  'reportsButton.setAttribute("aria-disabled", "true")',
  '(hasCompiledPostInterviewResult || key === "evidence")',
  'hasCompiledPostInterviewResult ? "overview" : "evidence"',
  'lastRenderedCompiled === false && hasCompiledPostInterviewResult',
  'const activeKey = keys.includes(key)',
  'if (reportsActive) activeReportKey = activeKey',
]) assert.ok(tabs.includes(snippet), "Report access/selection contract missing: " + snippet);

// Saved changes in question-specific notes are marked outdated by the
// existing module; unsaved general notes get an immediate visible warning.
for (const snippet of [
  'notesInput.value !== originalSavedNotes',
  'outputRoot?.dataset.postInterviewStatus === "outdated"',
  '"candidate-interview-question-note-updated"',
  'reportStatus.classList.toggle("needs-update", needsUpdate)',
  'reportsRefresh.classList.toggle("needs-update", needsUpdate)',
  'reportStatusTitle.textContent = hasUnsavedNotes',
  'reportStatusDetail.textContent = needsUpdate',
]) assert.ok(tabs.includes(snippet), "Report freshness contract missing: " + snippet);

// Both regenerate buttons delegate to the existing full-compilation action,
// which retains auto-save, privacy checks and manual-edit confirmations.
for (const snippet of [
  'evidenceCard.append(evidenceIntro, notesRoot, postSection)',
  'rebuildButton.dataset.afterInterviewRebuild = "evidence"',
  'reportsRefresh.dataset.afterInterviewRebuild = "reports"',
  "'[data-post-interview-generate][data-regenerate=\"true\"]'",
  'nativeButton.click()',
  'tabs.querySelectorAll("[data-after-interview-rebuild]")',
  "journeySteps.querySelectorAll",
]) assert.ok(tabs.includes(snippet), "Regeneration contract missing: " + snippet);
assert.ok(!tabs.includes("legacyGlobalRegenerate?.remove()"),
  "Existing regeneration button must remain mounted as action target.");
assert.ok(page.includes("window.saveCandidateInterviewNotes"), "Existing safe save action must remain available");
assert.ok(evidenceAvailability.includes('url.searchParams.set("structured", "1")'), "Question-only compilation must use structured overall picture");
assert.ok(evidenceAvailability.includes("drainPostInterviewStream(fullCompilationUrl(targetStreamUrl))"), "Full compile stream must preserve structured mode");
assert.ok(page.includes('url.searchParams.set("afterTab", "overview")') ||
          page.includes('afterInterviewUrl.searchParams.set("afterTab", "overview")'),
          "Post-compile refresh must land on overall picture.");

// Preserve prior journey, language support and saving.
for (const snippet of ["journeyTitle:", "journeySteps:", "evidenceHeading:", "evidenceHeadingReady:"]) {
  assert.ok(tabs.includes(snippet));
}
assert.ok(tabs.includes('reports: "Rapporter"'));
assert.ok(tabs.includes('reports: "Reports"'));
assert.ok(copy.includes("testresultat och processkontext"));
assert.ok(copy.includes("assessment results and process context"));
assert.ok(view.includes("data-interview-notes-save") && view.includes("data-post-interview-generate"));
assert.ok(view.includes('rows="8"'));
assert.ok(shell.includes("after-interview-tabs.js") && shell.includes("underlined-tabs-v6"));
assert.ok(header.includes("candidate-eyebrows.js") && header.includes("two-tabs-v3"));

// A compiled candidate sees only the single regenerate row on Evidence.
// Keep the original section hidden, not removed, so its stream handler stays active.
assert.ok(tabs.includes('if (hasCompiledPostInterviewResult) {\\n      // The original section')
  || tabs.includes('postSection.classList.add("d-none")'),
  "Compiled evidence should hide the duplicate post-interview section.");
assert.ok(tabs.includes('postSection.setAttribute("aria-hidden", "true")'),
  "Hidden internal regeneration controls should not enter the accessibility tree.");
assert.ok(tabs.includes('evidenceCard.append(evidenceIntro, notesRoot, postSection)'),
  "Original post-interview section must stay mounted.");
assert.ok(tabs.includes('rebuildDescription.textContent = copy().evidenceRebuildHint'),
  "Keep the single visible regeneration explanation.");
assert.ok(tabs.includes('rebuildButton.dataset.afterInterviewRebuild = "evidence"'),
  "Keep the regeneration action on the visible row.");

// Motivation layout: each factor gets a readable explanation and two guidance
// columns instead of placing three cramped cards side by side.
assert.ok(tabs.includes('grid-template-columns: minmax(0, 1fr); gap: 1rem;'),
  "Motivation factors should stack vertically.");
assert.ok(tabs.includes('after-interview-manager-report__motivator-intro'));
assert.ok(tabs.includes('after-interview-manager-report__motivator-practical'));
assert.ok(tabs.includes('motivatorIntro.append(name, definition)'));
assert.ok(tabs.includes('practical.append(practicalTitle, practicalGrid)'));
assert.ok(tabs.includes('group.type === "do" ? "check-circle" : "alert-circle"'));
assert.ok(/after-interview-manager-report__motivator-practical-grid\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\);/.test(tabs),
  "Advice boxes should stack on narrow screens.");

// The two navigation levels must share their real components with the
// Personality section, not just imitate them with a custom visual theme.
for (const snippet of [
  'primaryNav.className = "candidate-insights-view-switcher after-interview-primary-nav"',
  'reportNavWrapper.className = "personality-view-controls"',
  'reportNav.className = "personality-view-tabs"',
  'kind === "report"',
  '"personality-view-tab" : "candidate-insights-view-option"',
  'const button = makeTab(key, copy().tabs[key], id, "report")',
  'reportsButton.textContent = copy().tabs.reports',
]) assert.ok(tabs.includes(snippet), "Shared tab design is missing: " + snippet);

assert.ok(personalitySubtabs.includes('class="candidate-insights-view-switcher"'));
assert.ok(personalitySubtabs.includes('class="candidate-insights-view-option is-active"'));
assert.ok(personalityResults.includes('class="personality-view-tabs"'));
assert.ok(personalityResults.includes('class="personality-view-tab is-active"'));
assert.ok(sharedAssessmentStyles.includes('.process-page .candidate-insights-view-option'));
assert.ok(sharedAssessmentStyles.includes('.process-page .personality-view-tab'));
assert.ok(!tabs.includes('__PANEL__ .candidate-insights-view-option {'),
  "After interview must not override the shared primary tab appearance.");
assert.ok(!tabs.includes('__PANEL__ .after-interview-report-switcher {'),
  "After interview must not restyle the personality profile tabs.");

// Hide the redundant current-status callout, while retaining warnings
// for new or unsaved evidence and error feedback from regeneration.
assert.ok(tabs.includes("reportStatus.hidden = true"));
assert.ok(tabs.includes("reportStatus.hidden = !needsUpdate"));
assert.ok(tabs.includes('reportStatusTitle.textContent = hasUnsavedNotes'));
assert.ok(tabs.includes('reportStatus.hidden = false;'));
assert.ok(tabs.includes(".after-interview-reports__status[hidden]"));
assert.ok(!tabs.includes("reportStatusCurrent:"),
  "No current-compilation status text should be shown.");

// Primary tabs must match the text-only Team/Leadership/Derailment report tabs
// and override the rounded-pill assessment CSS only in After interview.
assert.ok(teamReportsTabs.includes('class="candidate-insights-view-option is-active"'));
assert.ok(reportTabStyles.includes('.candidate-insight-page .candidate-insights-view-option'));
for (const snippet of [
  'button.textContent = label;',
  'reportsButton.textContent = copy().tabs.reports;',
  'after-interview-primary-nav .candidate-insights-view-option.is-active',
  'border-bottom: 2px solid transparent !important;',
  'border-bottom-color: var(--talena-coral, #ff6f61) !important;',
  'border-radius: 0 !important;',
  'background: transparent !important;',
]) assert.ok(tabs.includes(snippet), "Text-underlined tabs: " + snippet);
assert.ok(!tabs.includes('reportsButton.append(reportsIcon, reportsText)'));
assert.ok(tabs.includes('reportNav.className = "personality-view-tabs"'),
  "Nested report tabs must retain the personality-style appearance.");

console.log("After interview Teamreport-style primary tabs contract passed.");
