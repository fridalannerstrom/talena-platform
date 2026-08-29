(() => {
  "use strict";

  const ChartLibrary = window.TeamStyleChartJS;

  if (
    !ChartLibrary
    || typeof ChartLibrary.register !== "function"
    || window.__talenaTeamStyleHoverFixRegistered
  ) {
    return;
  }

  const teamStyleHoverFixPlugin = {
    id: "talenaTeamStyleHoverFix",

    beforeDatasetDraw(chart, args) {
      const canvas = chart?.canvas;

      if (!canvas?.matches("[data-team-style-chart]")) {
        return;
      }

      const datasetIndex = Number.isInteger(args?.index)
        ? args.index
        : 0;

      const arcs = chart.getDatasetMeta(datasetIndex)?.data || [];

      arcs.forEach((arc) => {
        if (!arc?.options) {
          return;
        }

        /*
         * Chart.js can resolve borderRadius again when an arc becomes active.
         * Keep hover geometry identical to the resting team-style rose.
         */
        arc.options.borderRadius = 0;
        arc.options.hoverBorderRadius = 0;
        arc.options.offset = 0;
        arc.options.hoverOffset = 0;
      });
    },
  };

  ChartLibrary.register(teamStyleHoverFixPlugin);
  window.__talenaTeamStyleHoverFixRegistered = true;

  document
    .querySelectorAll("[data-team-style-chart]")
    .forEach((canvas) => {
      const chart = canvas._teamStyleChartInstance;

      if (chart && typeof chart.update === "function") {
        chart.update("none");
      }
    });
})();
