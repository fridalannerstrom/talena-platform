(() => {
  "use strict";

  /*
   * Canvas theme adapter for the motivation rose and team-style polar chart.
   *
   * Both charts are created inside process_base.html and own local afterDraw
   * plugins. Talena wraps those local plugins so the final labels, separators
   * and colours are drawn in one deterministic pass, including hover redraws.
   */

  const DOMAIN_PALETTE = [
    { rgb: [239, 94, 82] },
    { rgb: [207, 137, 127] },
    { rgb: [126, 162, 143] },
    { rgb: [197, 151, 79] },
  ];

  const TEAM_STYLE_PALETTE = {
    explore: DOMAIN_PALETTE[0],
    lead: DOMAIN_PALETTE[1],
    deliver: DOMAIN_PALETTE[2],
    review: DOMAIN_PALETTE[3],
  };

  const OPACITY_BY_SCORE = {
    1: 0.38,
    2: 0.52,
    3: 0.68,
    4: 0.84,
    5: 0.96,
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
        const score = Number(
          String(element.dataset.factorScore || "")
            .replace(",", ".")
        );
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

  function getTeamStyleItems(canvas) {
    const root = canvas.closest("[data-team-style-chart-root]");

    if (!root) {
      return [];
    }

    return Array.from(
      root.querySelectorAll("[data-team-style-chart-item]")
    )
      .map((element) => {
        const score = Number(element.dataset.styleScore);

        return {
          name: element.dataset.styleName || "",
          score,
          quadrantKey: element.dataset.quadrantKey || "explore",
          quadrantLabel: element.dataset.quadrantLabel || "",
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
    const opacity = OPACITY_BY_SCORE[item.score] || 0.68;

    return `rgba(${palette.rgb[0]}, ${palette.rgb[1]}, ${palette.rgb[2]}, ${opacity})`;
  }

  function teamStylePaletteFor(item) {
    const palette = TEAM_STYLE_PALETTE[item.quadrantKey] || DOMAIN_PALETTE[0];
    const opacity = OPACITY_BY_SCORE[item.score] || 0.68;

    return `rgba(${palette.rgb[0]}, ${palette.rgb[1]}, ${palette.rgb[2]}, ${opacity})`;
  }

  function applyRenderedArcTheme(chart, colours) {
    const arcs = chart?.getDatasetMeta?.(0)?.data || [];
    const dataset = chart?.data?.datasets?.[0];

    if (!dataset || !arcs.length) {
      return;
    }

    arcs.forEach((arc, index) => {
      const colour = colours[index];

      if (!arc?.options || !colour) {
        return;
      }

      arc.options.backgroundColor = colour;
      arc.options.hoverBackgroundColor = colour;
      arc.options.borderColor = "#ffffff";
      arc.options.hoverBorderColor = "#ffffff";
      arc.options.borderWidth = dataset.borderWidth;
      arc.options.hoverBorderWidth = dataset.borderWidth;
      arc.options.offset = 0;
      arc.options.hoverOffset = 0;
    });
  }

  function applyDatasetTheme(chart) {
    const canvas = chart?.canvas;
    const dataset = chart?.data?.datasets?.[0];

    if (!canvas?.matches("[data-motivation-rose-chart]") || !dataset) {
      return [];
    }

    const items = getRoseItems(canvas);

    if (!items.length) {
      return [];
    }

    const colours = items.map(paletteFor);

    dataset.backgroundColor = colours;
    dataset.hoverBackgroundColor = colours;
    dataset.borderColor = "#ffffff";
    dataset.hoverBorderColor = "#ffffff";
    dataset.hoverBorderWidth = dataset.borderWidth;
    dataset.hoverOffset = 0;

    applyRenderedArcTheme(chart, colours);

    return colours;
  }

  function applyTeamStyleDatasetTheme(chart) {
    const canvas = chart?.canvas;
    const dataset = chart?.data?.datasets?.[0];

    if (!canvas?.matches("[data-team-style-chart]") || !dataset) {
      return [];
    }

    const items = getTeamStyleItems(canvas);

    if (!items.length) {
      return [];
    }

    const compact = canvas.clientWidth < 620;
    const colours = items.map(teamStylePaletteFor);

    dataset.backgroundColor = colours;
    dataset.hoverBackgroundColor = colours;
    dataset.borderColor = "#ffffff";
    dataset.hoverBorderColor = "#ffffff";
    dataset.borderWidth = compact ? 2 : 3;
    dataset.hoverBorderWidth = dataset.borderWidth;
    dataset.borderRadius = compact ? 7 : 12;
    dataset.spacing = compact ? 1 : 2;
    dataset.hoverOffset = 0;

    applyRenderedArcTheme(chart, colours);

    return colours;
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

  function wrapLabel(value, maxLength) {
    const words = String(value || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean);

    const lines = [];
    let currentLine = "";

    words.forEach((word) => {
      const nextLine = currentLine ? `${currentLine} ${word}` : word;

      if (nextLine.length > maxLength && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = nextLine;
      }
    });

    if (currentLine) {
      lines.push(currentLine);
    }

    return lines.slice(0, 2);
  }

  function drawTeamStyleOverlay(chart) {
    const canvas = chart?.canvas;

    if (!canvas?.matches("[data-team-style-chart]")) {
      return;
    }

    const items = getTeamStyleItems(canvas);
    const arcs = chart.getDatasetMeta(0)?.data || [];
    const radialScale = chart.scales?.r;

    if (!items.length || !arcs.length || !radialScale) {
      return;
    }

    const compact = canvas.clientWidth < 620;
    const centerX = radialScale.xCenter;
    const centerY = radialScale.yCenter;
    const drawingArea = radialScale.drawingArea;
    const styleLabelRadius = drawingArea + (compact ? 18 : 28);
    const quadrantLabelRadius = drawingArea + (compact ? 48 : 68);
    const ctx = chart.ctx;

    ctx.save();

    /* Only show the four meaningful area boundaries, like the motivation rose. */
    items.forEach((item, index) => {
      const previous = items[(index - 1 + items.length) % items.length];
      const arc = arcs[index];

      if (!arc || previous?.quadrantKey === item.quadrantKey) {
        return;
      }

      const angle = arc.startAngle;

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

    /* Team-style names are always visible, so hover is optional rather than required. */
    items.forEach((item, index) => {
      const arc = arcs[index];

      if (!arc) {
        return;
      }

      const angle = (arc.startAngle + arc.endAngle) / 2;
      const cosine = Math.cos(angle);
      const sine = Math.sin(angle);
      const labelX = centerX + cosine * styleLabelRadius;
      const labelY = centerY + sine * styleLabelRadius;
      const labelLines = wrapLabel(item.name, compact ? 11 : 16);

      if (cosine > 0.25) {
        ctx.textAlign = "left";
      } else if (cosine < -0.25) {
        ctx.textAlign = "right";
      } else {
        ctx.textAlign = "center";
      }

      ctx.textBaseline = "middle";
      ctx.fillStyle = "#475467";
      ctx.font = compact
        ? "600 9px Inter, system-ui, sans-serif"
        : "600 11px Inter, system-ui, sans-serif";

      const lineHeight = compact ? 11 : 14;
      const firstLineY = labelY - ((labelLines.length - 1) * lineHeight) / 2;

      labelLines.forEach((line, lineIndex) => {
        ctx.fillText(
          line,
          labelX,
          firstLineY + lineIndex * lineHeight
        );
      });

      const scoreRadius = Math.max(
        arc.innerRadius + 16,
        arc.outerRadius - (compact ? 13 : 17)
      );
      const scoreX = centerX + cosine * scoreRadius;
      const scoreY = centerY + sine * scoreRadius;

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#ffffff";
      ctx.font = compact
        ? "700 9px Inter, system-ui, sans-serif"
        : "700 11px Inter, system-ui, sans-serif";
      ctx.fillText(String(item.score), scoreX, scoreY);
    });

    /* Place each area heading outside its two styles using a circular mean. */
    const quadrants = new Map();

    items.forEach((item, index) => {
      const arc = arcs[index];

      if (!arc) {
        return;
      }

      const angle = (arc.startAngle + arc.endAngle) / 2;
      const current = quadrants.get(item.quadrantKey) || {
        label: item.quadrantLabel,
        cosine: 0,
        sine: 0,
      };

      current.cosine += Math.cos(angle);
      current.sine += Math.sin(angle);
      quadrants.set(item.quadrantKey, current);
    });

    quadrants.forEach((quadrant) => {
      const angle = Math.atan2(quadrant.sine, quadrant.cosine);
      const x = centerX + Math.cos(angle) * quadrantLabelRadius;
      const y = centerY + Math.sin(angle) * quadrantLabelRadius;

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#171312";
      ctx.font = compact
        ? "800 12px Inter, system-ui, sans-serif"
        : "800 16px Inter, system-ui, sans-serif";
      ctx.fillText(String(quadrant.label || ""), x, y);
    });

    ctx.restore();
  }

  function findLocalLabelsPlugin(chart, pluginId) {
    const candidates = [];

    if (Array.isArray(chart?.config?.plugins)) {
      candidates.push(...chart.config.plugins);
    }

    if (Array.isArray(chart?.config?._config?.plugins)) {
      candidates.push(...chart.config._config.plugins);
    }

    return candidates.find(
      (plugin) => plugin && plugin.id === pluginId
    ) || null;
  }

  function patchLocalLabelsPlugin(chart) {
    if (!chart || chart.$talenaMotivationLocalPluginPatched) {
      return Boolean(chart?.$talenaMotivationLocalPluginPatched);
    }

    const plugin = findLocalLabelsPlugin(chart, "motivationRoseLabels");

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

  function patchTeamStyleLabelsPlugin(chart) {
    if (!chart || chart.$talenaTeamStyleLocalPluginPatched) {
      return Boolean(chart?.$talenaTeamStyleLocalPluginPatched);
    }

    const plugin = findLocalLabelsPlugin(chart, "teamStyleThemeLabels");

    if (!plugin || typeof plugin.afterDraw !== "function") {
      return false;
    }

    /* Replace the legacy coloured corner headings with the Talena rose hierarchy. */
    plugin.afterDraw = function talenaTeamStyleAfterDraw(currentChart) {
      drawTeamStyleOverlay(currentChart);
    };

    plugin.$talenaWrapped = true;
    chart.$talenaTeamStyleLocalPluginPatched = true;

    return true;
  }

  function patchChartDraw(chart) {
    if (!chart || chart.$talenaMotivationDrawPatched) {
      return;
    }

    const originalDraw = chart.draw;

    if (typeof originalDraw !== "function") {
      return;
    }

    chart.draw = function talenaMotivationDraw(...args) {
      applyDatasetTheme(this);
      return originalDraw.apply(this, args);
    };

    chart.$talenaMotivationDrawPatched = true;
  }

  function patchTeamStyleChartDraw(chart) {
    if (!chart || chart.$talenaTeamStyleDrawPatched) {
      return;
    }

    const originalDraw = chart.draw;

    if (typeof originalDraw !== "function") {
      return;
    }

    chart.draw = function talenaTeamStyleDraw(...args) {
      applyTeamStyleDatasetTheme(this);
      return originalDraw.apply(this, args);
    };

    chart.$talenaTeamStyleDrawPatched = true;
  }

  function themeMotivationRose(canvas) {
    const chart = canvas?._motivationRoseChartInstance;

    if (!chart) {
      return false;
    }

    applyDatasetTheme(chart);
    const patched = patchLocalLabelsPlugin(chart);
    patchChartDraw(chart);

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

    if (!patched) {
      drawDomainOverlay(chart);
    }

    return true;
  }

  function themeTeamStyleChart(canvas) {
    const chart = canvas?._teamStyleChartInstance;

    if (!chart) {
      return false;
    }

    const compact = canvas.clientWidth < 620;

    applyTeamStyleDatasetTheme(chart);
    const patched = patchTeamStyleLabelsPlugin(chart);
    patchTeamStyleChartDraw(chart);

    if (chart.options?.scales?.r) {
      const radial = chart.options.scales.r;

      if (radial.ticks) {
        radial.ticks.color = "#9c938e";
        radial.ticks.backdropColor = "rgba(255, 255, 255, 0.9)";
        radial.ticks.backdropPadding = 2;
        radial.ticks.font = {
          ...(radial.ticks.font || {}),
          size: compact ? 9 : 10,
        };
      }

      if (radial.grid) {
        radial.grid.color = "rgba(23, 19, 18, 0.10)";
      }

      if (radial.angleLines) {
        radial.angleLines.display = false;
      }

      if (radial.pointLabels) {
        radial.pointLabels.display = false;
      }
    }

    if (chart.options?.layout) {
      chart.options.layout.padding = compact
        ? {
            top: 64,
            right: 64,
            bottom: 64,
            left: 64,
          }
        : {
            top: 98,
            right: 105,
            bottom: 98,
            left: 105,
          };
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

    if (!patched) {
      drawTeamStyleOverlay(chart);
    }

    return true;
  }

  function themeAvailableCharts() {
    document
      .querySelectorAll("[data-motivation-rose-chart]")
      .forEach((canvas) => themeMotivationRose(canvas));

    document
      .querySelectorAll("[data-team-style-chart]")
      .forEach((canvas) => themeTeamStyleChart(canvas));
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
      event.target.closest("[data-insights-tab='team-styles']") ||
      event.target.closest("[data-insights-subtab]")
    ) {
      scheduleThemePasses();
    }
  });
})();
