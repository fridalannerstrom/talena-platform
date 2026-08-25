(() => {
  "use strict";

  /*
   * Transitional chart-brand layer.
   *
   * Most candidate visualisations are CSS-driven and now live in
   * candidate-charts.css. The motivation rose is rendered on canvas by
   * Chart.js inside the existing process script, so CSS cannot recolour it.
   * This small adapter keeps the canvas aligned with the Talena palette until
   * the chart initialisation code is extracted from process_base.html.
   */

  const DOMAIN_PALETTE = [
    { rgb: [231, 106, 94], solid: "#e76a5e" },
    { rgb: [201, 130, 118], solid: "#c98276" },
    { rgb: [126, 159, 139], solid: "#7e9f8b" },
    { rgb: [200, 154, 90], solid: "#c89a5a" },
  ];

  const OPACITY_BY_SCORE = {
    1: 0.34,
    2: 0.48,
    3: 0.64,
    4: 0.8,
    5: 0.94,
  };

  function getChartLibrary() {
    return window.TeamStyleChartJS || window.Chart || null;
  }

  function getRoseItems(canvas) {
    const root = canvas.closest("[data-motivation-rose-chart-root]");

    if (!root) {
      return [];
    }

    return Array.from(
      root.querySelectorAll("[data-motivation-rose-item]")
    )
      .map((element) => {
        const score = Number(element.dataset.factorScore);
        const domainIndex = Number(element.dataset.domainIndex);

        return {
          name: element.dataset.factorName || "",
          domain: element.dataset.factorDomain || "",
          score,
          domainIndex: Number.isFinite(domainIndex) ? domainIndex : 0,
        };
      })
      .filter((item) => Number.isFinite(item.score));
  }

  function buildDomainGroups(items) {
    const groups = [];

    items.forEach((item, index) => {
      const previous = groups[groups.length - 1];

      if (previous && previous.domainIndex === item.domainIndex) {
        previous.endIndex = index;
        return;
      }

      groups.push({
        domain: item.domain,
        domainIndex: item.domainIndex,
        startIndex: index,
        endIndex: index,
      });
    });

    return groups;
  }

  const talenaMotivationDomainPlugin = {
    id: "talenaMotivationDomainTheme",

    afterDraw(chart) {
      const canvas = chart?.canvas;

      if (!canvas?.matches("[data-motivation-rose-chart]")) {
        return;
      }

      const items = getRoseItems(canvas);
      const groups = buildDomainGroups(items);
      const arcs = chart.getDatasetMeta(0)?.data || [];
      const radialScale = chart.scales?.r;

      if (!items.length || !groups.length || !arcs.length || !radialScale) {
        return;
      }

      const compact = canvas.clientWidth < 620;
      const centerX = radialScale.xCenter;
      const centerY = radialScale.yCenter;
      const domainLabelRadius =
        radialScale.drawingArea + (compact ? 46 : 66);
      const ctx = chart.ctx;

      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = compact
        ? "750 9px Inter, system-ui, sans-serif"
        : "750 11px Inter, system-ui, sans-serif";

      groups.forEach((group) => {
        const firstArc = arcs[group.startIndex];
        const lastArc = arcs[group.endIndex];

        if (!firstArc || !lastArc) {
          return;
        }

        const middleAngle = (firstArc.startAngle + lastArc.endAngle) / 2;
        const palette =
          DOMAIN_PALETTE[group.domainIndex % DOMAIN_PALETTE.length];

        ctx.fillStyle = palette.solid;
        ctx.fillText(
          String(group.domain || "").toUpperCase(),
          centerX + Math.cos(middleAngle) * domainLabelRadius,
          centerY + Math.sin(middleAngle) * domainLabelRadius
        );
      });

      ctx.restore();
    },
  };

  function registerPlugin() {
    const ChartLibrary = getChartLibrary();

    if (!ChartLibrary || ChartLibrary.__talenaMotivationThemeRegistered) {
      return;
    }

    try {
      ChartLibrary.register(talenaMotivationDomainPlugin);
      ChartLibrary.__talenaMotivationThemeRegistered = true;
    } catch (error) {
      console.warn("[TALENA CHART THEME] Could not register chart plugin", error);
    }
  }

  function themeMotivationRose(canvas) {
    const chart = canvas?._motivationRoseChartInstance;

    if (!chart) {
      return false;
    }

    const items = getRoseItems(canvas);
    const dataset = chart.data?.datasets?.[0];

    if (!dataset || !items.length) {
      return false;
    }

    dataset.backgroundColor = items.map((item) => {
      const palette =
        DOMAIN_PALETTE[item.domainIndex % DOMAIN_PALETTE.length];
      const opacity = OPACITY_BY_SCORE[item.score] || 0.64;

      return `rgba(${palette.rgb[0]}, ${palette.rgb[1]}, ${palette.rgb[2]}, ${opacity})`;
    });

    dataset.borderColor = "#ffffff";
    dataset.hoverBorderColor = "#ffffff";

    if (chart.options?.scales?.r) {
      const radial = chart.options.scales.r;

      if (radial.ticks) {
        radial.ticks.color = "#9c938e";
        radial.ticks.backdropColor = "rgba(255, 255, 255, 0.9)";
      }

      if (radial.grid) {
        radial.grid.color = "rgba(23, 19, 18, 0.10)";
      }
    }

    chart.$talenaBrandTheme = true;
    chart.update("none");

    return true;
  }

  function themeAvailableCharts() {
    registerPlugin();

    document
      .querySelectorAll("[data-motivation-rose-chart]")
      .forEach((canvas) => themeMotivationRose(canvas));
  }

  function scheduleThemePasses() {
    [0, 80, 220, 600].forEach((delay) => {
      window.setTimeout(themeAvailableCharts, delay);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleThemePasses, {
      once: true,
    });
  } else {
    scheduleThemePasses();
  }

  document.addEventListener("click", (event) => {
    if (
      event.target.closest("[data-insights-tab='motivation']") ||
      event.target.closest("[data-insights-subtab]")
    ) {
      scheduleThemePasses();
    }
  });
})();
