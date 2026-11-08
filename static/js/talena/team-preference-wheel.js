/* #375: SVG-based composite team preference wheel.
   Aggregate extrema come from the already-authorised team statistics. No
   candidate data is fetched or recomputed on the client. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const CENTER = { x: 450, y: 445 };
  const ORDER = ["Catalyst", "Director", "Energiser", "Architect",
    "Harmoniser", "Analyst", "Auditor", "Connector"];
  const QUADRANT_COLORS = ["#9A366F", "#3E7DBA", "#31569D", "#75459E"];

  function readData(id) {
    const script = document.getElementById(id);
    if (!script) return null;
    try {
      return JSON.parse(script.textContent || "null");
    } catch (error) {
      console.warn("Invalid team wheel data.", error);
      return null;
    }
  }

  function node(tag, attributes, text) {
    const element = document.createElementNS(NS, tag);
    Object.entries(attributes || {}).forEach(function (entry) {
      element.setAttribute(entry[0], String(entry[1]));
    });
    if (text !== undefined) element.textContent = String(text);
    return element;
  }

  function point(radius, degrees) {
    const angle = degrees * Math.PI / 180;
    return {
      x: CENTER.x + Math.cos(angle) * radius,
      y: CENTER.y + Math.sin(angle) * radius
    };
  }

  function sector(inner, outer, start, end) {
    const a = point(outer, start);
    const b = point(outer, end);
    const c = point(inner, end);
    const d = point(inner, start);
    return [
      "M", a.x, a.y,
      "A", outer, outer, 0, 0, 1, b.x, b.y,
      "L", c.x, c.y,
      "A", inner, inner, 0, 0, 0, d.x, d.y,
      "Z"
    ].join(" ");
  }

  function labelMap(root) {
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

  function badge(layer, x, y, person, kind) {
    const g = node("g", {
      "data-team-wheel-person": "",
      "data-person-name": person.name || "",
      "class": "team-wheel-person"
    });
    g.appendChild(node("rect", {
      x: x - 20, y: y - 12, width: 40, height: 24,
      rx: 8, fill: "#ffffff", "fill-opacity": 0.84
    }));
    g.appendChild(node("text", {
      x: x, y: y + 4,
      "text-anchor": "middle",
      "font-size": "12",
      "font-weight": "700",
      "fill": kind === "most" ? "#245946" : "#873E52",
      "data-team-wheel-initial": ""
    }, person.initials || "?"));
    g.appendChild(node("title", {}, person.name || person.initials || ""));
    layer.appendChild(g);
  }

  function initialCluster(layer, candidates, radius, angle, kind, overflowLabel) {
    if (!Array.isArray(candidates) || !candidates.length) return;

    // Cap visible initials per sector to keep long teams readable. The
    // expandable accessible list below the wheel includes everyone.
    const maximum = kind === "most" ? 6 : 4;
    const overflow = candidates.length > maximum;
    const shown = overflow ? candidates.slice(0, maximum - 1) : candidates.slice();
    const entries = shown.map(function (person) { return { person: person }; });
    if (overflow) entries.push({ overflow: candidates.length - shown.length });

    const columns = kind === "most" ? 3 : 2;
    const center = point(radius, angle);
    const rows = Math.ceil(entries.length / columns);

    entries.forEach(function (entry, index) {
      const row = Math.floor(index / columns);
      const first = row * columns;
      const count = Math.min(columns, entries.length - first);
      const column = index - first;
      const x = center.x + (column - (count - 1) / 2) * 46;
      const y = center.y + (row - (rows - 1) / 2) * 30;

      if (entry.person) {
        badge(layer, x, y, entry.person, kind);
      } else {
        const more = node("g", { "class": "team-wheel-overflow" });
        more.appendChild(node("rect", {
          x: x - 20, y: y - 12, width: 40, height: 24, rx: 8,
          fill: "#ffffff", "fill-opacity": 0.62
        }));
        more.appendChild(node("text", {
          x: x, y: y + 4, "text-anchor": "middle", "font-size": 11,
          "font-weight": 700, fill: "#655953"
        }, "+" + entry.overflow));
        more.appendChild(node("title", {}, overflowLabel));
        layer.appendChild(more);
      }
    });
  }

  function createWheel(root, rows, labels, swedish) {
    const byStyle = new Map(rows.map(function (row) {
      return [row.style, row];
    }));
    const svg = node("svg", {
      xmlns: NS, viewBox: "0 0 900 890",
      class: "team-preference-wheel-svg",
      role: "img",
      "aria-label": root.dataset.wheelLabel || "Team preference wheel",
      preserveAspectRatio: "xMidYMid meet"
    });
    svg.appendChild(node("title", {},
      root.dataset.wheelLabel || "Team preference wheel"));

    const outer = node("g", { "class": "team-wheel-ring team-wheel-ring--most",
      "data-team-wheel-ring": "most" });
    const inner = node("g", { "class": "team-wheel-ring team-wheel-ring--least",
      "data-team-wheel-ring": "least" });
    const labelLayer = node("g", { "class": "team-wheel-labels" });
    const overflowLabel = root.dataset.wheelOverflowLabel || "See full list below";

    ORDER.forEach(function (style, index) {
      const angle = -112.5 + index * 45;
      const start = -135 + index * 45 + 0.8;
      const end = -90 + index * 45 - 0.8;
      const entry = byStyle.get(style) || {};
      const high = Array.isArray(entry.most) ? entry.most : [];
      const low = Array.isArray(entry.least) ? entry.least : [];
      const highFill = index % 2 ? "#AAD7C2" : "#B8E1CD";
      const lowFill = index % 2 ? "#F1C1CB" : "#F5CFD5";

      const highSegment = node("path", {
        d: sector(185, 283, start, end), fill: highFill,
        "data-team-wheel-sector": style, "data-wheel-preference": "most"
      });
      highSegment.appendChild(node("title", {},
        (labels[style] || style) + ": " +
        (entry.max == null ? "—" : entry.max + " / 5")));
      outer.appendChild(highSegment);
      initialCluster(outer, high, 234, angle, "most", overflowLabel);

      const lowSegment = node("path", {
        d: sector(88, 180, start, end), fill: lowFill,
        "data-team-wheel-sector": style, "data-wheel-preference": "least"
      });
      lowSegment.appendChild(node("title", {},
        (labels[style] || style) + ": " +
        (entry.min == null ? "—" : entry.min + " / 5")));
      inner.appendChild(lowSegment);
      initialCluster(inner, low, 133, angle, "least", overflowLabel);

      const p = point(323, angle);
      const cosine = Math.cos(angle * Math.PI / 180);
      const anchor = cosine > 0.62 ? "start" : cosine < -0.62 ? "end" : "middle";
      labelLayer.appendChild(node("text", {
        x: p.x, y: p.y + 4, "text-anchor": anchor,
        fill: "#403A38", "font-size": "16", "font-weight": "650"
      }, labels[style] || style));
    });

    svg.appendChild(node("circle", {
      cx: CENTER.x, cy: CENTER.y, r: 289,
      fill: "none", stroke: "#ECE7E2", "stroke-width": 1
    }));
    svg.appendChild(outer);
    svg.appendChild(inner);
    svg.appendChild(node("circle", {
      cx: CENTER.x, cy: CENTER.y, r: 82,
      fill: "#ffffff", stroke: "#E8E4E0", "stroke-width": 2
    }));
    svg.appendChild(node("text", {
      x: CENTER.x, y: CENTER.y - 24, "text-anchor": "middle",
      "font-size": 13, "font-weight": "750", "letter-spacing": 1.5,
      fill: "#A77D70"
    }, "TALENA"));
    svg.appendChild(node("text", {
      x: CENTER.x, y: CENTER.y + 4, "text-anchor": "middle",
      "font-size": 19, "font-weight": "780", fill: "#342E2D"
    }, swedish ? "Teamprofil" : "Team profile"));
    svg.appendChild(node("text", {
      x: CENTER.x, y: CENTER.y + 28, "text-anchor": "middle",
      "font-size": 12, "font-weight": "600", fill: "#827670"
    }, (root.dataset.membersCount || "0") + " " +
      (root.dataset.wheelMemberLabel || "")));

    const quadrants = swedish
      ? ["UTFORSKA", "LEDA", "LEVERERA", "KRITISKT GRANSKA"]
      : ["EXPLORING", "DIRECTING", "DELIVERING", "CRITIQUING"];
    const positions = [
      [250, 68], [650, 68], [650, 828], [250, 828]
    ];
    quadrants.forEach(function (text, index) {
      labelLayer.appendChild(node("text", {
        x: positions[index][0], y: positions[index][1],
        "text-anchor": "middle",
        "font-size": 17, "font-weight": 780,
        "letter-spacing": 0.8, fill: QUADRANT_COLORS[index]
      }, text));
    });
    svg.appendChild(labelLayer);
    root.replaceChildren(svg);
    return { outer: outer, inner: inner };
  }

  function init() {
    const root = document.getElementById("teamStylePreferenceWheel");
    if (!root || root.dataset.wheelReady === "true") return;

    const rows = readData("team-style-wheel-people");
    const styles = readData("team-style-chart-labels");
    if (!Array.isArray(rows) || !Array.isArray(styles) ||
        !ORDER.every(function (style) {
          return styles.includes(style) && rows.some(function (row) {
            return row.style === style;
          });
        })) return;

    const swedish = (document.documentElement.lang || "")
      .toLowerCase().startsWith("sv");
    const labels = labelMap(root);
    const parts = createWheel(root, rows, labels, swedish);
    const section = root.closest("[data-team-report-composite]");
    const buttons = section
      ? Array.from(section.querySelectorAll("[data-team-wheel-mode]")) : [];

    function selectMode(mode) {
      if (!["both", "most", "least"].includes(mode)) return;
      root.dataset.wheelMode = mode;
      parts.outer.setAttribute("visibility", mode === "least" ? "hidden" : "visible");
      parts.inner.setAttribute("visibility", mode === "most" ? "hidden" : "visible");
      buttons.forEach(function (button) {
        const active = button.dataset.teamWheelMode === mode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        selectMode(button.dataset.teamWheelMode);
      });
    });
    root.dataset.wheelReady = "true";
    selectMode("both");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
