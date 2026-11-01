/* #367: Keep the compact status icons in sync with per-assessment Sova data. */
(function () {
  "use strict";
  const STATUS_TONES = new Set(["success", "info", "warning", "muted"]);
  const STATUS_STATES = new Set([
    "not_sent", "not_started", "started", "completed", "invited",
    "expired", "failed", "activity_failed", "not_assigned", "unknown"
  ]);

  function start(root) {
    const endpoint = root.dataset.statusUrl;
    if (!endpoint) return;

    const byCell = new Map();
    root.querySelectorAll("[data-assessment-status]").forEach(cell => {
      byCell.set(cell.dataset.invitationId + ":" + cell.dataset.testKey, cell);
    });
    if (!byCell.size) return;

    // Bootstrap tooltips escape the horizontally scrolling table, unlike
    // pseudo-element tooltips. Native title remains as a safe fallback.
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
        // Tapping a status on a touch device should explain the icon,
        // without opening the candidate row.
        cell.addEventListener("click", event => {
          if (!window.matchMedia || !window.matchMedia("(hover: none)").matches) return;
          event.stopPropagation();
          cell.focus();
          const tooltip = typeof Tooltip.getInstance === "function"
            ? Tooltip.getInstance(cell) : null;
          if (tooltip) tooltip.show();
        });
      });
    }

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
            if (!cell || !STATUS_TONES.has(assessment.tone) ||
                !STATUS_STATES.has(assessment.state)) return;

            const label = cell.querySelector(".talena-assessment-state__label");
            const path = cell.querySelector(".talena-assessment-state__symbol path");
            const nextClass = "talena-assessment-state talena-assessment-state--" + assessment.tone;
            const title = assessment.title;
            const accessibleLabel = assessment.title;

            if (cell.className !== nextClass) cell.className = nextClass;
            if (cell.dataset.state !== assessment.state) cell.dataset.state = assessment.state;
            if (label && label.textContent !== assessment.label) {
              label.textContent = assessment.label;
            }
            if (path && typeof assessment.icon_path === "string" &&
                path.getAttribute("d") !== assessment.icon_path) {
              path.setAttribute("d", assessment.icon_path);
            }
            const tooltip = Tooltip && typeof Tooltip.getInstance === "function"
              ? Tooltip.getInstance(cell) : null;
            if (tooltip) {
              if (cell.getAttribute("data-bs-original-title") !== title) {
                cell.setAttribute("data-bs-original-title", title);
                if (typeof tooltip.setContent === "function") {
                  tooltip.setContent({ ".tooltip-inner": title });
                }
              }
            } else if (cell.title !== title) {
              cell.title = title;
            }
            if (cell.getAttribute("aria-label") !== accessibleLabel) {
              cell.setAttribute("aria-label", accessibleLabel);
            }
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
