/* Ticket #359, first slice: centralized, branded PDF exports of existing
 * authorized candidate report results. No network requests or AI calls.
 * The registry/API is reused by #360 report-package selection later.
 */
(function () {
  "use strict";
  if (window.TalenaCandidateReportPdf) return;

  const REPORTS = Object.freeze([
    { id: "overview", panel: "overview", label: { sv: "Sammanfattning", en: "Overview" }, availability: "any" },
    { id: "personality-results", panel: "personality", subpanel: "results", label: { sv: "Personlighet · Resultat", en: "Personality · Results" }, availability: "personality" },
    { id: "motivation-results", panel: "motivation", subpanel: "results", label: { sv: "Motivation · Resultat", en: "Motivation · Results" }, availability: "motivation" },
    { id: "cognitive-results", panel: "cognitive", subpanel: "results", label: { sv: "Färdighet · Resultat", en: "Skills · Results" }, availability: "cognitive" },
    { id: "team-profile", panel: "reports", subpanel: "team-report", label: { sv: "Individuell teamrapport", en: "Individual team report" }, availability: "teamProfile" },
    { id: "leadership-profile", panel: "reports", subpanel: "leadership-report", label: { sv: "Ledarskapsrapport", en: "Leadership report" }, availability: "leadership" },
    { id: "derailment-profile", panel: "reports", subpanel: "derailment-report", label: { sv: "Urspårningsrapport", en: "Derailment report" }, availability: "derailment" }
  ]);

  const translations = {
    sv: {
      button: "Ladda ner PDF-rapport",
      downloading: "Skapar PDF…",
      success: "PDF-rapporten har laddats ner.",
      failed: "Kunde inte skapa PDF-rapporten. Försök igen.",
      unavailable: "Rapporten är inte tillgänglig ännu.",
      coverSubtitle: "Kandidatrapport",
      notReady: "Rapporten innehåller inga färdiga resultat."
    },
    en: {
      button: "Download PDF report",
      downloading: "Creating PDF…",
      success: "The PDF report has been downloaded.",
      failed: "The PDF report could not be created. Please try again.",
      unavailable: "This report is not available yet.",
      coverSubtitle: "Candidate report",
      notReady: "The report has no completed results."
    }
  };

  function language() {
    return document.documentElement.lang?.toLowerCase().startsWith("sv") ? "sv" : "en";
  }
  function displayName(report) {
    return report.label[language()];
  }
  function getReport(id) {
    return REPORTS.find(report => report.id === id) || null;
  }
  function hasResults(workspace, report) {
    if (!report) return false;
    if (report.availability === "any") return true;
    return workspace.dataset["reportHas" + report.availability[0].toUpperCase() + report.availability.slice(1)] === "true";
  }
  function getSource(workspace, report) {
    if (!workspace || !report || !hasResults(workspace, report)) return null;
    // Never select a panel outside THIS candidate workspace.
    const panel = Array.from(workspace.querySelectorAll("[data-insights-panel]"))
      .find(el => el.dataset.insightsPanel === report.panel);
    if (!panel) return null;
    if (!report.subpanel) return panel;
    return Array.from(panel.querySelectorAll("[data-insights-subpanel]"))
      .find(el => el.dataset.insightsSubpanel === report.subpanel) || null;
  }

  function availableReports(workspace) {
    return REPORTS.filter(report => Boolean(getSource(workspace, report)))
      .map(report => ({ id: report.id, title: displayName(report), panel: report.panel, subpanel: report.subpanel || null }));
  }

  function createCover(workspace, report) {
    const primary = /^#[a-f\d]{6}$/i.test(workspace.dataset.reportBrandPrimary || "")
      ? workspace.dataset.reportBrandPrimary : "#FF6F61";
    const root = document.createElement("header");
    root.className = "candidate-pdf-cover";
    root.style.setProperty("--candidate-pdf-primary", primary);
    const focus = Number(workspace.dataset.reportBrandFocus);
    root.style.backgroundPosition = "center " +
      (Number.isFinite(focus) ? Math.max(0, Math.min(100, focus)) : 50) + "%";
    const photo = workspace.dataset.reportBrandCover;
    if (photo) root.style.backgroundImage =
      'linear-gradient(180deg,rgba(0,0,0,.16),rgba(0,0,0,.76)),url("' + photo.replace(/"/g, "%22") + '")';

    const brand = document.createElement("div");
    brand.className = "candidate-pdf-brand";
    if (workspace.dataset.reportBrandLogo) {
      const img = document.createElement("img");
      img.src = workspace.dataset.reportBrandLogo;
      img.alt = "";
      brand.append(img);
    } else {
      brand.classList.add("candidate-pdf-brand--fallback");
      brand.textContent = workspace.dataset.reportBrandCompany || "Talena";
    }

    const title = document.createElement("div");
    title.className = "candidate-pdf-cover-title";
    const rule = document.createElement("div");
    rule.className = "candidate-pdf-rule";
    const kicker = document.createElement("p");
    kicker.textContent = translations[language()].coverSubtitle;
    const h1 = document.createElement("h1");
    h1.textContent = displayName(report);
    const company = document.createElement("p");
    company.textContent = workspace.dataset.reportBrandCompany || "Talena";
    title.append(rule, kicker, h1, company);
    root.append(brand, title);
    return root;
  }

  function isVisible(element) {
    return !element.hidden && !element.closest("[hidden], .d-none, .visually-hidden, [aria-hidden='true']");
  }

  function copyReport(source) {
    const clone = source.cloneNode(true);
    clone.removeAttribute("hidden");
    clone.classList.remove("d-none");

    // Snapshot charts BEFORE stripping hidden widgets. Original and cloned
    // NodeLists have identical order at this point, even when canvases lack
    // an id. Skipping hidden original charts avoids exporting stale graphs.
    const originals = Array.from(source.querySelectorAll("canvas"));
    const copied = Array.from(clone.querySelectorAll("canvas"));
    if (originals.length !== copied.length) throw new Error("Chart cloning failed.");
    copied.forEach((canvas, index) => {
      const original = originals[index];
      if (!isVisible(original)) return; // Hidden graph removed below.
      if (!original.width || !original.height) {
        throw new Error("Report chart is not ready.");
      }
      const image = document.createElement("img");
      image.src = original.toDataURL("image/png");
      image.alt = canvas.getAttribute("aria-label") || "";
      image.className = "candidate-pdf-chart";
      canvas.replaceWith(image);
    });

    // Keep only visible, previously rendered content. Hidden AI placeholders,
    // interactive controls and editable/unsaved candidate notes are excluded.
    clone.querySelectorAll(
      "button, input, textarea, select, form, " +
      ".candidate-insights-subnavigation, .candidate-insights-navigation, " +
      "[data-report-pdf-toolbar], .after-interview-manager-report__edit-controls, " +
      "[hidden], .d-none, .visually-hidden, [aria-hidden='true'], " +
      "[data-pre-interview-thinking], [data-post-interview-thinking], " +
      ".spinner-border, .btn, .toast, .modal, .dropdown-menu"
    ).forEach(node => node.remove());

    // Never retain private state in data-* or onclick attributes.
    clone.querySelectorAll("*").forEach(node => {
      for (const attribute of Array.from(node.attributes)) {
        if (attribute.name.startsWith("data-") || attribute.name.startsWith("on")) {
          node.removeAttribute(attribute.name);
        }
      }
    });
    return clone;
  }

  function assertReady(source, report) {
    // "AI interpretation" and interview report types are intentionally not
    // registered until their saved/ready status can be checked accurately.
    if (!source || !source.textContent || source.textContent.trim().length < 30) {
      throw new Error(translations[language()].notReady);
    }
    const activeVisibleText = Array.from(source.querySelectorAll("p, h2, h3, h4, td, .team-style-rank-score"))
      .filter(isVisible).map(x => (x.textContent || "").trim()).join(" ");
    if (!activeVisibleText.trim() && !source.querySelector("canvas, svg, table")) {
      throw new Error(translations[language()].notReady);
    }
    if (source.querySelector("[data-status='generating']:not(.d-none), [data-status='in_progress']:not(.d-none)")) {
      throw new Error(translations[language()].notReady);
    }
  }

  async function exportReport(workspace, reportId, options = {}) {
    const report = getReport(reportId);
    const source = getSource(workspace, report);
    if (!source) throw new Error(translations[language()].unavailable);
    assertReady(source, report);
    if (!window.TalenaPdfExport?.exportSections) throw new Error("PDF engine unavailable");

    const stage = document.createElement("div");
    stage.className = "candidate-insights-workspace candidate-pdf-stage";
    stage.style.setProperty("--candidate-pdf-accent", workspace.dataset.reportBrandPrimary || "#FF6F61");
    stage.style.setProperty("--candidate-pdf-accent-light", workspace.dataset.reportBrandLight || "#FFF0ED");
    stage.style.setProperty("--candidate-pdf-accent-dark", workspace.dataset.reportBrandDark || "#C94D41");
    const cover = createCover(workspace, report);
    const main = document.createElement("main");
    main.className = "candidate-pdf-body";
    const heading = document.createElement("h2");
    heading.className = "candidate-pdf-content-title";
    heading.textContent = displayName(report);
    main.append(heading);
    try {
      main.append(copyReport(source));
      stage.append(cover, main);
      document.body.append(stage);
      return await window.TalenaPdfExport.exportSections(
        [{ node: cover, cover: true }, { node: main, continuous: true }],
        {
          title: displayName(report),
          subject: "Talena candidate assessment report",
          filename: "talena-" + report.id + ".pdf",
          returnBlob: Boolean(options.returnBlob),
          onProgress: options.onProgress
        }
      );
    } finally {
      stage.remove();
    }
  }

  function createToolbar(workspace, report) {
    const source = getSource(workspace, report);
    if (!source || Array.from(source.children).some(el => el.matches("[data-report-pdf-toolbar]"))) return;
    const toolbar = document.createElement("div");
    toolbar.className = "candidate-pdf-toolbar";
    toolbar.dataset.reportPdfToolbar = report.id;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-outline-secondary btn-sm";
    button.textContent = translations[language()].button;
    const status = document.createElement("span");
    status.className = "candidate-pdf-status small";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    toolbar.append(button, status);
    source.insertBefore(toolbar, source.firstChild);
    button.addEventListener("click", async () => {
      if (button.disabled) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      status.textContent = translations[language()].downloading;
      status.classList.remove("text-danger");
      try {
        await exportReport(workspace, report.id);
        status.textContent = translations[language()].success;
      } catch (error) {
        status.textContent = error.message === translations[language()].notReady
          ? error.message : translations[language()].failed;
        status.classList.add("text-danger");
      } finally {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }
    });
  }

  function init(root) {
    const workspaces = Array.from((root || document).querySelectorAll("[data-candidate-insights-workspace]"));
    if (root?.matches?.("[data-candidate-insights-workspace]")) workspaces.unshift(root);
    workspaces.forEach(workspace => {
      REPORTS.forEach(report => createToolbar(workspace, report));
    });
  }

  window.TalenaCandidateReportPdf = Object.freeze({
    registry: REPORTS,
    availableReports,
    exportReport,
    init
  });
})();
