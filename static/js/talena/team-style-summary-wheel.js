/* Ticket #527: switch between the aggregate SVG views on the team report. */
(function () {
  "use strict";

  function init() {
    document.querySelectorAll("[data-team-summary-wheel]").forEach(function (section) {
      const charts = Array.from(section.querySelectorAll("[data-team-summary-chart]"));
      const buttons = Array.from(section.querySelectorAll("[data-team-summary-mode]"));
      if (!charts.length || !buttons.length) return;

      function selectMode(mode) {
        charts.forEach(function (chart) {
          chart.hidden = chart.dataset.teamSummaryChart !== mode;
        });
        buttons.forEach(function (button) {
          const active = button.dataset.teamSummaryMode === mode;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", String(active));
        });
      }

      buttons.forEach(function (button) {
        button.addEventListener("click", function () {
          selectMode(button.dataset.teamSummaryMode);
        });
      });
      selectMode("average");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
