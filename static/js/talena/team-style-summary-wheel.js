/* Ticket #527: team-level averages and extrema in the SOVA-style circular chart. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const ORDER = ["Catalyst", "Director", "Energiser", "Architect",
    "Harmoniser", "Analyst", "Auditor", "Connector"];
  const QUADRANT_COLORS = {
    Catalyst: "#9A366F", Connector: "#9A366F",
    Director: "#3E7DBA", Energiser: "#3E7DBA",
    Architect: "#31569D", Harmoniser: "#31569D",
    Analyst: "#75459E", Auditor: "#75459E"
  };
  const CENTER = { x: 380, y: 380 };
  const MAX_RADIUS = 244;

  function readJson(id) {
    const node = document.getElementById(id);
    if (!node) return null;
    try {
      return JSON.parse(node.textContent || "null");
    } catch (error) {
      console.warn("Invalid team style summary data.", error);
      return null;
    }
  }

  function svgNode(tag, attributes, value) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attributes || {}).forEach(function (entry) {
      node.setAttribute(entry[0], String(entry[1]));
    });
    if (value !== undefined) node.textContent = String(value);
    return node;
  }

  function point(radius, degrees) {
    const angle = degrees * Math.PI / 180;
    return {
      x: CENTER.x + Math.cos(angle) * radius,
      y: CENTER.y + Math.sin(angle) * radius
    };
  }

  function sector(radius, start, end) {
    const first = point(radius, start);
    const last = point(radius, end);
    return [
      "M", CENTER.x, CENTER.y,
      "L", first.x, first.y,
      "A", radius, radius, 0, 0, 1, last.x, last.y,
      "Z"
    ].join(" ");
  }

  function labelsFrom(root) {
    return {
      Connector: root.dataset.styleConnector || "Connector",
      Catalyst: root.dataset.styleCatalyst || "Catalyst",
      Director: root.dataset.styleDirector || "Director",
      Energiser: root.dataset.styleEnergiser || "Energiser",
      Architect: root.dataset.styleArchitect || "Architect",
      Harmoniser: root.dataset.styleHarmoniser || "Harmoniser",
      Analyst: root.dataset.styleAnalyst || "Analyst",
      Auditor: root.dataset.styleAuditor || "Auditor"
    };
  }

  function getModeData(mode) {
    const source = {
      average: "team-style-chart-averages",
      minimum: "team-style-chart-min",
      maximum: "team-style-chart-max"
    }[mode];
    const values = readJson(source);
    return Array.isArray(values) ? values : [];
  }

  function draw(root, mode) {
    const labels = readJson("team-style-chart-labels");
    const values = getModeData(mode);
    if (!Array.isArray(labels) || labels.length !== ORDER.length ||
        values.length !== ORDER.length) return;

    const labelsByStyle = labelsFrom(root);
    const modeLabels = {
      average: root.dataset.averageLabel || "Average",
      minimum: root.dataset.minimumLabel || "Minimum",
      maximum: root.dataset.maximumLabel || "Maximum"
    };
    const svg = svgNode("svg", {
      viewBox: "0 0 760 760",
      class: "team-summary-wheel-svg",
      role: "img",
      "aria-label": root.dataset.wheelLabel || "Team style summary"
    });
    svg.appendChild(svgNode("title", {},
      (root.dataset.wheelLabel || "Team style summary") + " · " + modeLabels[mode]));

    // Subtle one-point rings keep the 1–5 scale visible without competing
    // with the exact values printed in each segment.
    const gridLayer = svgNode("g", { "aria-hidden": "true" });
    for (let score = 1; score <= 5; score += 1) {
      gridLayer.appendChild(svgNode("circle", {
        cx: CENTER.x, cy: CENTER.y,
        r: (score / 5) * MAX_RADIUS,
        class: "team-summary-wheel-grid"
      }));
    }

    const sectorLayer = svgNode("g", { "aria-hidden": "true" });
    const labelLayer = svgNode("g", {});
    const valueLayer = svgNode("g", {});

    ORDER.forEach(function (style, index) {
      const value = values[index];
      const valid = value !== null && value !== undefined && Number.isFinite(Number(value));
      const numeric = valid ? Math.max(0, Math.min(5, Number(value))) : null;
      const angle = -112.5 + index * 45;
      const start = -135 + index * 45 + 1.2;
      const end = -90 + index * 45 - 1.2;
      const radius = numeric === null ? 0 : (numeric / 5) * MAX_RADIUS;
      const fill = QUADRANT_COLORS[style] || "#7B7775";
      const slice = svgNode("path", {
        d: sector(radius, start, end),
        fill: fill,
        "fill-opacity": valid ? "0.78" : "0.06",
        stroke: "#ffffff",
        "stroke-width": "2",
        class: "team-summary-wheel-sector"
      });
      const displayValue = valid ? numeric.toFixed(1) : "—";
      slice.appendChild(svgNode("title", {},
        labelsByStyle[style] + " · " + modeLabels[mode] + ": " +
        displayValue + (valid ? " / 5" : "")));
      sectorLayer.appendChild(slice);

      const labelRadius = numeric === null
        ? 91
        : Math.max(88, Math.min(MAX_RADIUS - 24, radius * 0.61));
      const valuePoint = point(labelRadius, angle);
      valueLayer.appendChild(svgNode("text", {
        x: valuePoint.x,
        y: valuePoint.y + 5,
        "text-anchor": "middle",
        class: "team-summary-wheel-value",
        fill: numeric !== null && numeric >= 2.1 ? "#ffffff" : "#514745"
      }, displayValue));

      const labelPoint = point(315, angle);
      labelLayer.appendChild(svgNode("text", {
        x: labelPoint.x,
        y: labelPoint.y + 4,
        "text-anchor": "middle",
        class: "team-summary-wheel-label"
      }, labelsByStyle[style]));
    });

    svg.appendChild(sectorLayer);
    svg.appendChild(gridLayer);
    svg.appendChild(valueLayer);
    svg.appendChild(svgNode("circle", {
      cx: CENTER.x, cy: CENTER.y, r: 55,
      class: "team-summary-wheel-center"
    }));
    svg.appendChild(svgNode("text", {
      x: CENTER.x, y: CENTER.y - 2,
      "text-anchor": "middle", class: "team-summary-wheel-center-label"
    }, modeLabels[mode]));
    svg.appendChild(svgNode("text", {
      x: CENTER.x, y: CENTER.y + 20,
      "text-anchor": "middle", class: "team-summary-wheel-center-scale"
    }, "1–5"));
    svg.appendChild(labelLayer);
    root.replaceChildren(svg);
  }

  function init() {
    const root = document.getElementById("teamStyleSummaryWheel");
    if (!root || root.dataset.wheelReady === "true") return;
    const section = root.closest("[data-team-summary-wheel]");
    if (!section) return;
    const buttons = Array.from(section.querySelectorAll("[data-team-summary-mode]"));

    function selectMode(mode) {
      if (!["average", "minimum", "maximum"].includes(mode)) return;
      draw(root, mode);
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
    root.dataset.wheelReady = "true";
    selectMode("average");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
