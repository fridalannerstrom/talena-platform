(() => {
  "use strict";

  /*
   * Transitional chart-brand layer.
   *
   * Most candidate visualisations are CSS-driven and now live in
   * candidate-charts.css. The motivation rose is rendered on canvas by
   * Chart.js inside the existing process script, so CSS cannot recolour it.
   * Keep all Talena-specific canvas styling here until that chart setup is
   * extracted from process_base.html.
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

  function paletteFor(item) {
    const palette = DOMAIN_PALETTE[item.domainIndex % DOMAIN_PALETTE.length];
    const opacity = OPACITY_BY_SCORE[item.score] || 0.64;

    return `rgba(${palette.rgb[0]}, ${palette.rgb[1]}, ${palette.rgb[2]}, ${opacity})`;
  }

  function applyDatasetTheme(chart) {
    const canvas = chart?.canvas;

    if (!canvas?.matches("[data-motivation-rose-chart]")) {
      return;
    }

    const items = getRoseItems(canvas);
    const dataset = chart.data?.datasets?.[0];

    if (!dataset || !items.length) {
      return;
    }

    /*
     * This runs for every Chart.js render, including hover renders. That is
     * important because the original motivation chart is initialised with the
     * older purple/blue palette in process_base.html.
     */
    dataset.backgroundColor = items.map(paletteFor);
    dataset.hoverBackgroundColor = items.map(paletteFor);
    dataset.borderColor = "#ffffff";
    dataset.hoverBorderColor = "#ffffff";
    dataset.hoverBorderWidth = dataset.borderWidth;
    dataset.hoverOffset = 0;
  }

  function drawDomainOverlay(chart) {
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
    const drawingArea = radialScale.drawingArea;
    const domainLabelRadius = drawingArea + (compact ? 47 : 68);
    const ctx = chart.ctx;

    ctx.save();

    /*
     * Draw all four domain boundaries. The legacy local plugin draws white
     * separators; this final render-stage overlay replaces that hierarchy with
     * the darker Talena dividers requested for the motivation profile.
     */
    groups.forEach((group) => {
      const firstArc = arcs[group.startIndex];

      if (!firstArc) {
        return;
      }

      const angle = firstArc.startAngle;

      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(
        centerX + Math.cos(angle) * drawingArea,
        centerY + Math.sin(angle) * drawingArea
      );
      ctx.strokeStyle = "rgba(23, 19, 18, 0.26)";
      ctx.lineWidth = compact ? 1.6 : 2.1;
      ctx.stroke();
    });

    /*
     * Domain headings are hierarchy labels, not data colours. Clear the old
     * coloured heading and redraw it with Talena's primary text colour.
     */
    groups.forEach((group) => {
      const firstArc = arcs[group.startIndex];
      const lastArc = arcs[group.endIndex];

      if (!firstArc || !lastArc) {
        return;
      }

      const middleAngle = (firstArc.startAngle + lastArc.endAngle) / 2;
      const domainX = centerX + Math.cos(middleAngle) * domainLabelRadius;
      const domainY = centerY + Math.sin(middleAngle) * domainLabelRadius;
      const label = String(group.domain || "").toUpperCase();
      const font = compact
        ? "800 10.5px Inter, system-ui, sans-serif"
        : "800 13px Inter, system-ui, sans-serif";

      ctx.font = font;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const measured = ctx.measureText(label);
      const clearWidth = measured.width + (compact ? 8 : 12);
      const clearHeight = compact ? 17 : 21;

      ctx.clearRect(
        domainX - clearWidth / 2,
        domainY - clearHeight / 2,
        clearWidth,
        clearHeight
      );

      ctx.fillStyle = "#171312";
      ctx.fillText(label, domainX, domainY);
    });

    ctx.restore();
  }

  const talenaMotivationDomainPlugin = {
    id: "talenaMotivationDomainTheme",

    /*
     * Enforce the Talena palette immediately before datasets are painted.
     * This makes newly created charts and all hover redraws deterministic.
     */
    beforeDatasetsDraw(chart) {
      applyDatasetTheme(chart);
    },

    /*
     * afterRender runs after the chart's own local afterDraw plugin. This is
     * the key to avoiding the old/new hover flicker: the black headings and
     * dark domain separators are now the final synchronous canvas operation
     * for every render, rather than an animation-frame patch afterwards.
     */
    afterRender(chart) {
      drawDomainOverlay(chart);
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

    applyDatasetTheme(chart);

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

    /*
     * Keep the tooltip, but remove active-element movement. There should be no
     * visual jump when moving between factors.
     */
    if (chart.options) {
      chart.options.transitions = chart.options.transitions || {};
      chart.options.transitions.active = {
        animation: {
          duration: 0,
        },
      };
    }

    chart.$talenaBrandTheme = true;
    chart.update("none");
    drawDomainOverlay(chart);

    return true;
  }

  function themeAvailableCharts() {
    registerPlugin();

    document
      .querySelectorAll("[data-motivation-rose-chart]")
      .forEach((canvas) => themeMotivationRose(canvas));
  }

  function scheduleThemePasses() {
    [0, 80, 220, 600, 1200].forEach((delay) => {
      window.setTimeout(themeAvailableCharts, delay);
    });
  }

  /* Register as early as possible so charts created later inherit the plugin. */
  registerPlugin();

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
