"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const template = fs.readFileSync(
  "templates/customer/processes/process_base.html",
  "utf8"
);
const start = template.indexOf("async function refreshCandidateFinalOutput(");
const end = template.indexOf("\n}\n</script>", start);
assert.notEqual(start, -1, "final output refresh function exists in the candidate template");
assert.notEqual(end, -1, "final output refresh function ends before its script tag");

const functionSource = template.slice(start, end + 2);

function createHarness({ responseOk = true, validRoot = true, hasAfterInterviewPanel = true, language = "sv" } = {}) {
  const calls = { errors: [], order: [] };
  const actionButton = {};
  const currentSelectedTab = {
    dataset: { afterInterviewTab: "managerReport" },
    contains: () => false,
  };
  const currentTabPanel = {
    dataset: { afterInterviewTabPanel: "managerReport" },
    contains: element => element === actionButton,
  };
  const refreshedSelectedTab = {
    dataset: { afterInterviewTab: "managerReport" },
    focus(options) { calls.focus = options; calls.order.push("focus"); },
  };
  const currentAfterInterviewPanel = {};
  const refreshedAfterInterviewPanel = {};
  const insightsTab = {
    dataset: { insightsTab: "after-interview" },
    click() {
      calls.outerTabReactivated = Boolean(calls.replacedWith);
      calls.order.push("outer-tab");
    },
  };
  const insightsWorkspace = {
    querySelector(selector) {
      return selector.includes(".candidate-profile-tabs")
        && selector.includes(".is-active")
        ? insightsTab
        : null;
    },
    querySelectorAll(selector) {
      return selector.includes(".candidate-profile-tabs")
        ? [insightsTab]
        : [];
    },
  };

  const currentRoot = {
    dataset: { refreshUrl: "/candidate/final-output/refresh/" },
    closest: selector =>
      selector === "[data-candidate-insights-workspace]" ? insightsWorkspace : null,
    querySelector(selector) {
      if (selector.includes("data-after-interview-tab")) return currentSelectedTab;
      if (selector.includes("data-insights-panel")) return currentAfterInterviewPanel;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === "[data-after-interview-tab-panel]") return [currentTabPanel];
      return [];
    },
    replaceWith(node) { calls.replacedWith = node; },
  };

  const refreshedRoot = {
    matches: selector => validRoot && selector === "[data-final-output-root]",
    querySelector: selector =>
      selector.includes("data-insights-panel") && hasAfterInterviewPanel
        ? refreshedAfterInterviewPanel
        : null,
    querySelectorAll: selector =>
      selector === "[data-after-interview-tab]" ? [refreshedSelectedTab] : [],
  };

  const document = {
    activeElement: actionButton,
    createElement(tag) {
      assert.equal(tag, "template");
      const result = { content: { firstElementChild: null } };
      Object.defineProperty(result, "innerHTML", {
        set() { result.content.firstElementChild = refreshedRoot; },
      });
      return result;
    },
  };
  const initialUrl = `https://talena.example/candidate/?language=${language}`;
  const window = {
    location: { href: initialUrl },
    history: { replaceState(_state, _title, url) { calls.url = String(url); window.location.href = String(url); } },
    initAfterInterviewTabs(root) {
      calls.initialized = root;
      calls.activeTabAtInitialization = new URL(window.location.href).searchParams.get("afterTab");
      calls.order.push("inner-init");
    },
  };
  const context = {
    document,
    window,
    URL,
    fetch: async () => ({
      ok: responseOk,
      text: async () => "<div data-final-output-root></div>",
    }),
    console: { error: (...args) => calls.errors.push(args) },
  };

  const refresh = vm.runInNewContext(
    `${functionSource}\nrefreshCandidateFinalOutput;`,
    context,
    { filename: "process_base.html" }
  );
  return { refresh, currentRoot, refreshedRoot, calls };
}

(async () => {
  for (const language of ["sv", "en"]) {
    const { refresh, currentRoot, refreshedRoot, calls } = createHarness({ language });
    await refresh({ querySelector: () => currentRoot });
    assert.equal(calls.replacedWith, refreshedRoot, "replace the old root with the validated response");
    assert.equal(calls.outerTabReactivated, true, "reapply the active outer After interview tab after replacement");
    assert.equal(calls.initialized, refreshedRoot, "initialize the inner interview tabs before paint");
    assert.equal(calls.activeTabAtInitialization, "managerReport", "rebuild the same active report tab");
    assert.equal(calls.order.join(","), "outer-tab,inner-init,focus", "restore the outer panel before the inner tab and focus");
    assert.equal(new URL(calls.url).searchParams.get("language"), language, "preserve other URL state");
    assert.equal(new URL(calls.url).searchParams.get("afterTab"), "managerReport");
    assert.equal(calls.focus?.preventScroll, true, "restore focus to the active report tab");
    assert.equal(calls.errors.length, 0);
  }

  for (const options of [
    { validRoot: false },
    { hasAfterInterviewPanel: false },
    { responseOk: false },
  ]) {
    const bad = createHarness(options);
    await bad.refresh({ querySelector: () => bad.currentRoot });
    assert.equal(bad.calls.replacedWith, undefined, "keep the current report when the refresh response is invalid or incomplete");
    assert.equal(bad.calls.outerTabReactivated, undefined, "do not switch tabs when refresh failed");
    assert.equal(bad.calls.initialized, undefined, "do not initialize a failed refresh");
    assert.equal(bad.calls.errors.length, 1, "record the failed refresh for diagnostics");
  }

  console.log("After interview final output refresh smoke passed.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
