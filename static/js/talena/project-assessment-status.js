/* Ticket #367: update only the per-assessment cells from project-scoped polling. */
(function () {
  "use strict";
  const STATUS_TONES = new Set(["success", "info", "warning", "muted"]);
  function start(root) {
    const endpoint = root.dataset.statusUrl;
    if (!endpoint) return;
    const byCell = new Map();
    root.querySelectorAll("[data-assessment-status]").forEach(cell => {
      byCell.set(cell.dataset.invitationId + ":" + cell.dataset.testKey, cell);
    });
    if (!byCell.size) return;
    async function refresh() {
      if (document.hidden) return;
      try {
        const response = await fetch(endpoint, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        if (!response.ok) return;
        const payload = await response.json();
        (payload.invitations || []).forEach(inv => {
          (inv.assessments || []).forEach(assessment => {
            const cell = byCell.get(String(inv.id) + ":" + assessment.key);
            if (!cell || !STATUS_TONES.has(assessment.tone)) return;
            const label = cell.querySelector(".talena-assessment-state__label");
            const icon = cell.querySelector(".talena-assessment-state__icon");
            const nextClass = "talena-assessment-state talena-assessment-state--" + assessment.tone;
            if (cell.className !== nextClass) cell.className = nextClass;
            if (label && label.textContent !== assessment.label) label.textContent = assessment.label;
            if (icon && icon.textContent !== assessment.icon) icon.textContent = assessment.icon;
            if (cell.title !== assessment.title) cell.title = assessment.title;
            if (cell.getAttribute("aria-label") !== assessment.title) cell.setAttribute("aria-label", assessment.title);
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
