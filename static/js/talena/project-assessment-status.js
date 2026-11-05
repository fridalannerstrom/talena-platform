/* #367/#447: Keep project test statuses and verified percentiles in sync. */
(function () {
  "use strict";
  const STATUS_TONES = new Set(["success", "info", "warning", "muted"]);
  const STATUS_STATES = new Set([
    "not_sent", "not_started", "started", "completed", "invited",
    "expired", "failed", "activity_failed", "not_assigned", "unknown"
  ]);
  const COGNITIVE_KEYS = new Set(["logical", "numerical", "verbal"]);
  let pendingFocusObserver = null;

  function verifiedPercentile(assessment) {
    return assessment.state === "completed"
      && COGNITIVE_KEYS.has(assessment.key)
      && assessment.has_percentile === true
      && Number.isInteger(assessment.percentile)
      && assessment.percentile >= 0 && assessment.percentile <= 100;
  }

  function focusCognitiveResultOnOpen(candidateLink, testKey) {
    const sheetBody = document.getElementById("candidateSheetBody");
    if (!sheetBody || !COGNITIVE_KEYS.has(testKey)) return;
    if (pendingFocusObserver) pendingFocusObserver.disconnect();

    let timeout;
    const observer = new MutationObserver(() => {
      // Watch only sheet-body replacement, not the live charts/AI inside it.
      const card = sheetBody.querySelector(
        '[data-insights-panel="cognitive"] [data-manager-skill-key="' + testKey + '"]'
      );
      if (!card) return;
      observer.disconnect();
      pendingFocusObserver = null;
      window.clearTimeout(timeout);

      // Candidate sheet handlers are bound after the AJAX HTML is inserted.
      window.requestAnimationFrame(() => {
        const workspace = card.closest("[data-candidate-insights-workspace]");
        const tab = workspace && workspace.querySelector(
          '.candidate-profile-tabs [data-insights-tab="cognitive"]'
        );
        const subtab = card.closest('[data-insights-panel="cognitive"]')
          ?.querySelector('[data-insights-subtab="results"]');
        if (tab) tab.click();
        if (subtab) subtab.click();

        if (!card.closest("[hidden]")) {
          card.tabIndex = -1;
          card.focus({ preventScroll: true });
          card.scrollIntoView({ behavior: "smooth", block: "center" });
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
    const nextClass = "talena-assessment-state talena-assessment-state--"
      + assessment.tone + (hasPercentile ? " talena-assessment-state--percentile" : "");
    const title = String(assessment.title || "");
    const label = cell.querySelector(".talena-assessment-state__label");
    const symbol = cell.querySelector(".talena-assessment-state__symbol");
    const path = symbol && symbol.querySelector("path");
    const percentileButton = cell.querySelector("[data-assessment-percentile-button]");

    if (cell.className !== nextClass) cell.className = nextClass;
    if (cell.dataset.state !== assessment.state) cell.dataset.state = assessment.state;
    cell.dataset.hasPercentile = hasPercentile ? "true" : "false";
    cell.setAttribute("role", hasPercentile ? "group" : "img");
    cell.tabIndex = hasPercentile ? -1 : 0;
    if (label && label.textContent !== assessment.label) label.textContent = assessment.label;
    if (path && typeof assessment.icon_path === "string"
        && path.getAttribute("d") !== assessment.icon_path) {
      path.setAttribute("d", assessment.icon_path);
    }
    if (symbol) symbol.hidden = hasPercentile;
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
          if (cell.dataset.hasPercentile === "true") return;
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
      const button = event.target.closest("[data-assessment-percentile-button]");
      if (!button || button.hidden) return;
      event.preventDefault();
      event.stopPropagation();
      const candidateLink = button.closest("tr")?.querySelector("a.js-open-candidate");
      if (!candidateLink || !COGNITIVE_KEYS.has(button.dataset.focusTestKey)) return;
      focusCognitiveResultOnOpen(candidateLink, button.dataset.focusTestKey);
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