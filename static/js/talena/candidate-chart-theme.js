(() => {
  "use strict";

  /*
   * Canvas theme adapter for the motivation rose.
   *
   * The chart itself is still created inside process_base.html. That chart
   * owns a local `motivationRoseLabels` plugin which draws factor labels,
   * domain headings and the original white domain separators on every canvas
   * redraw, including hover/tooltip redraws.
   *
   * Rather than competing with that plugin from a second global plugin, Talena
   * wraps the local plugin once and performs its final hierarchy styling at
   * the end of the SAME synchronous afterDraw pass. This removes the hover
   * flicker and gives the chart one deterministic visual state.
   */

  const DOMAIN_PALETTE = [
    { rgb: [255, 111, 97] },
    { rgb: [228, 162, 155] },
    { rgb: [157, 183, 168] },
    { rgb: [215, 176, 110] },
  ];

  const OPACITY_BY_SCORE = {
    1: 0.34,
    2: 0.48,
    3: 0.64,
    4: 0.8,
    5: 0.94,
  };

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
    const dataset = chart?.data?.datasets?.[0];

    if (!canvas?.matches("[data-motivation-rose-chart]") || !dataset) {
      return;
    }

    const items = getRoseItems(canvas);

    if (!items.length) {
      return;
    }

    const colours = items.map(paletteFor);

    dataset.backgroundColor = colours;
    dataset.hoverBackgroundColor = colours;
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
    const domainLabelRadius = drawingArea + (compact ? 49 : 72);
    const ctx = chart.ctx;

    ctx.save();

    /* Four clear boundaries, including the join between last and first area. */
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

    /* Larger black area headings, using normal title casing. */
    groups.forEach((group) => {
      const firstArc = arcs[group.startIndex];
      const lastArc = arcs[group.endIndex];

      if (!firstArc || !lastArc) {
        return;
      }

      const middleAngle = (firstArc.startAngle + lastArc.endAngle) / 2;
      const domainX = centerX + Math.cos(middleAngle) * domainLabelRadius;
      const domainY = centerY + Math.sin(middleAngle) * domainLabelRadius;
      const label = String(group.domain || "");

      ctx.font = compact
        ? "800 12px Inter, system-ui, sans-serif"
        : "800 16px Inter, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      /* Remove the coloured legacy heading that was drawn immediately before. */
      const measured = ctx.measureText(label);
      const clearWidth = measured.width + (compact ? 12 : 18);
      const clearHeight = compact ? 22 : 28;

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

  function findLocalLabelsPlugin(chart) {
    const candidates = [];

    if (Array.isArray(chart?.config?.plugins)) {
      candidates.push(...chart.config.plugins);
    }

    if (Array.isArray(chart?.config?._config?.plugins)) {
      candidates.push(...chart.config._config.plugins);
    }

    return candidates.find(
      (plugin) => plugin && plugin.id === "motivationRoseLabels"
    ) || null;
  }

  function patchLocalLabelsPlugin(chart) {
    if (!chart || chart.$talenaMotivationLocalPluginPatched) {
      return Boolean(chart?.$talenaMotivationLocalPluginPatched);
    }

    const plugin = findLocalLabelsPlugin(chart);

    if (!plugin || typeof plugin.afterDraw !== "function") {
      return false;
    }

    const originalAfterDraw = plugin.afterDraw;

    plugin.afterDraw = function talenaMotivationAfterDraw(
      currentChart,
      args,
      options
    ) {
      originalAfterDraw.call(this, currentChart, args, options);
      drawDomainOverlay(currentChart);
    };

    plugin.$talenaWrapped = true;
    chart.$talenaMotivationLocalPluginPatched = true;

    return true;
  }

  function themeMotivationRose(canvas) {
    const chart = canvas?._motivationRoseChartInstance;

    if (!chart) {
      return false;
    }

    applyDatasetTheme(chart);
    const patched = patchLocalLabelsPlugin(chart);

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

    /* Fallback for an unexpected Chart.js config shape. */
    if (!patched) {
      drawDomainOverlay(chart);
    }

    return true;
  }

  function themeAvailableCharts() {
    document
      .querySelectorAll("[data-motivation-rose-chart]")
      .forEach((canvas) => themeMotivationRose(canvas));
  }

  function scheduleThemePasses() {
    [0, 80, 220, 600, 1200].forEach((delay) => {
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
