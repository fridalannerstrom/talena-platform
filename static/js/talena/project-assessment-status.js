/* #367/#447: Keep project test statuses and verified percentiles in sync. */
(function () {
  "use strict";
  const STATUS_TONES = new Set(["success", "info", "warning", "muted"]);
  const STATUS_STATES = new Set([
    "not_sent", "not_started", "started", "completed", "invited",
    "expired", "failed", "activity_failed", "not_assigned", "unknown"
  ]);
  const COGNITIVE_KEYS = new Set(["logical", "numerical", "verbal"]);
  const CHECKMARK_SHORTCUT_KEYS = new Set(["personality", "motivation"]);
  let pendingFocusObserver = null;

  function verifiedPercentile(assessment) {
    return assessment.state === "completed"
      && COGNITIVE_KEYS.has(assessment.key)
      && assessment.has_percentile === true
      && Number.isInteger(assessment.percentile)
      && assessment.percentile >= 0 && assessment.percentile <= 100;
  }

  function focusAssessmentResultOnOpen(testKey) {
    const sheetBody = document.getElementById("candidateSheetBody");
    const panelKey = COGNITIVE_KEYS.has(testKey) ? "cognitive" : testKey;
    if (!sheetBody || (!COGNITIVE_KEYS.has(testKey)
        && !CHECKMARK_SHORTCUT_KEYS.has(testKey))) return;
    if (pendingFocusObserver) pendingFocusObserver.disconnect();

    let timeout;
    const observer = new MutationObserver(() => {
      const workspace = sheetBody.querySelector("[data-candidate-insights-workspace]");
      const panel = workspace && workspace.querySelector(
        '[data-insights-panel="' + panelKey + '"]'
      );
      const card = COGNITIVE_KEYS.has(testKey) && panel
        ? panel.querySelector('[data-manager-skill-key="' + testKey + '"]')
        : null;
      if (!workspace || !panel || (COGNITIVE_KEYS.has(testKey) && !card)) return;
      observer.disconnect();
      pendingFocusObserver = null;
      window.clearTimeout(timeout);

      // The customer candidate sheet attaches handlers immediately after
      // injecting HTML. Wait one frame before invoking its ordinary tab click.
      window.requestAnimationFrame(() => {
        if (!workspace.isConnected) return;
        const tab = workspace.querySelector(
          '.candidate-profile-tabs [data-insights-tab="' + panelKey + '"]'
        );
        if (!tab) return;
        tab.click();
        const resultsTab = panel.querySelector('[data-insights-subtab="results"]');
        if (resultsTab) resultsTab.click();

        if (card && !card.closest("[hidden]")) {
          card.tabIndex = -1;
          card.focus({ preventScroll: true });
          card.scrollIntoView({ behavior: "smooth", block: "center" });
        } else {
          // Keep keyboard focus on the destination when opening PQ or MQ.
          tab.focus({ preventScroll: true });
        }
      });
    });
    pendingFocusObserver = observer;
    observer.observe(sheetBody, { childList: true });
    timeout = window.setTimeout(() => {
      observer.disconnect();
      if (pendingFocusObserver === observer) pendingFocusObserver = null;
    }, 15000);
  }

  function updateCell(cell, assessment, Tooltip) {
    const hasPercentile = verifiedPercentile(assessment);
    const hasShortcut = assessment.state === "completed"
      && CHECKMARK_SHORTCUT_KEYS.has(assessment.key)
      && assessment.has_shortcut === true;
    const nextClass = "talena-assessment-state talena-assessment-state--"
      + assessment.tone + (hasPercentile ? " talena-assessment-state--percentile" : "")
      + (hasShortcut ? " talena-assessment-state--shortcut" : "");
    const title = String(assessment.title || "");
    const label = cell.querySelector(".talena-assessment-state__label");
    const symbol = cell.querySelector(".talena-assessment-state__symbol");
    const path = symbol && symbol.querySelector("path");
    const percentileButton = cell.querySelector("[data-assessment-percentile-button]");
    const checkmarkButton = cell.querySelector("[data-assessment-result-button]");

    if (cell.className !== nextClass) cell.className = nextClass;
    if (cell.dataset.state !== assessment.state) cell.dataset.state = assessment.state;
    cell.dataset.hasPercentile = hasPercentile ? "true" : "false";
    cell.dataset.hasShortcut = hasShortcut ? "true" : "false";
    cell.setAttribute("role", hasPercentile || hasShortcut ? "group" : "img");
    cell.tabIndex = hasPercentile || hasShortcut ? -1 : 0;
    if (label && label.textContent !== assessment.label) label.textContent = assessment.label;
    if (path && typeof assessment.icon_path === "string"
        && path.getAttribute("d") !== assessment.icon_path) {
      path.setAttribute("d", assessment.icon_path);
    }
    if (symbol) symbol.hidden = hasPercentile;
    if (checkmarkButton) {
      checkmarkButton.hidden = !hasShortcut;
      checkmarkButton.setAttribute("aria-label", assessment.shortcut_label || "");
    }
    if (percentileButton) {
      percentileButton.hidden = !hasPercentile;
      percentileButton.textContent = hasPercentile ? String(assessment.percentile) : "";
      percentileButton.setAttribute("title", title);
      percentileButton.setAttribute("aria-label", title);
    }

    if (cell.getAttribute("title") !== title) cell.setAttribute("title", title);
    if (cell.getAttribute("aria-label") !== title) cell.setAttribute("aria-label", title);
    const tooltip = Tooltip && typeof Tooltip.getInstance === "function"
      ? Tooltip.getInstance(cell) : null;
    if (tooltip && cell.getAttribute("data-bs-original-title") !== title) {
      cell.setAttribute("data-bs-original-title", title);
      if (typeof tooltip.setContent === "function") {
        tooltip.setContent({ ".tooltip-inner": title });
      }
    }
  }

  function start(root) {
    const endpoint = root.dataset.statusUrl;
    if (!endpoint) return;

    const byCell = new Map();
    root.querySelectorAll("[data-assessment-status]").forEach(cell => {
      byCell.set(cell.dataset.invitationId + ":" + cell.dataset.testKey, cell);
    });
    if (!byCell.size) return;

    const Tooltip = window.bootstrap && window.bootstrap.Tooltip;
    if (Tooltip) {
      byCell.forEach(cell => {
        const existing = typeof Tooltip.getInstance === "function"
          ? Tooltip.getInstance(cell) : null;
        if (!existing) {
          new Tooltip(cell, {
            container: "body",
            customClass: "talena-assessment-tooltip",
            trigger: "hover focus",
            placement: "top",
            delay: { show: 120, hide: 80 }
          });
        }
        cell.addEventListener("click", event => {
          if (cell.dataset.hasPercentile === "true"
              || cell.dataset.hasShortcut === "true") return;
          if (!window.matchMedia || !window.matchMedia("(hover: none)").matches) return;
          event.stopPropagation();
          cell.focus();
          const tooltip = typeof Tooltip.getInstance === "function"
            ? Tooltip.getInstance(cell) : null;
          if (tooltip) tooltip.show();
        });
      });
    }

    root.addEventListener("click", event => {
      const button = event.target.closest(
        "[data-assessment-percentile-button], [data-assessment-result-button]"
      );
      if (!button || button.hidden) return;
      const testKey = button.dataset.focusTestKey;
      const cognitive = button.hasAttribute("data-assessment-percentile-button");
      if (cognitive ? !COGNITIVE_KEYS.has(testKey)
                    : !CHECKMARK_SHORTCUT_KEYS.has(testKey)) return;
      event.preventDefault();
      event.stopPropagation();
      const candidateLink = button.closest("tr")?.querySelector("a.js-open-candidate");
      if (!candidateLink) return;
      focusAssessmentResultOnOpen(testKey);
      // Reuse the existing candidate-sheet handler and its project/tenant checks.
      candidateLink.click();
    });

    async function refresh() {
      if (document.hidden) return;
      try {
        const response = await fetch(endpoint, {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        if (!response.ok) return;
        const payload = await response.json();

        (payload.invitations || []).forEach(inv => {
          (inv.assessments || []).forEach(assessment => {
            const cell = byCell.get(String(inv.id) + ":" + assessment.key);
            if (!cell || !STATUS_TONES.has(assessment.tone)
                || !STATUS_STATES.has(assessment.state)) return;
            updateCell(cell, assessment, Tooltip);
          });
        });
      } catch (_) {
        // Preserve the last known snapshot if the network is unavailable.
      }
    }

    refresh();
    window.setInterval(refresh, 5000);
  }

  function init() {
    document.querySelectorAll("[data-project-test-statuses]").forEach(start);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();