/* #359: report types for the current authorised candidate; reusable by #360.
 * PDF rendering is entirely client side. It never sends assessment data to
 * Sova/OpenAI or fetches another person's/project's report.
 */
(() => {
  "use strict";
  if (window.TalenaCandidateReports) return;
  // Candidate sheets are loaded by AJAX into an offcanvas *after* page load.
  // Keep a stable export API and bind it to the currently displayed sheet.
  let workspace = null;
  let observer = null;
  const sv = (document.documentElement.lang || "").toLowerCase().startsWith("sv");
  const copy = sv ? {
    action: "Ladda ner PDF-rapport", busy: "Skapar PDF…",
    unavailable: "PDF tillgänglig när innehållet är klart.",
    outdated: "Uppdatera tolkningen före export.",
    error: "PDF:en kunde inte skapas. Försök igen.",
    success: "PDF-rapporten har laddats ner."
  } : {
    action: "Download PDF report", busy: "Creating PDF…",
    unavailable: "PDF available when the content is ready.",
    outdated: "Update the interpretation before exporting.",
    error: "The PDF could not be created. Please try again.",
    success: "PDF report downloaded."
  };
  const title = sv ? {
    overview: "Överblick", personality: "Personlighet", motivation: "Motivation",
    cognitive: "Färdighet", results: "Resultat",
    interpretation: "AI-tolkning", questions: "Intervjufrågor",
    "candidate-reflection": "Kandidatens reflektioner",
    "team-report": "Individuell teamprofil",
    "leadership-report": "Ledarskapsrapport", "derailment-report": "Urspårningsrapport",
    "prepare-interview": "Inför intervju", "after-overview": "Helhetsbild",
    "after-interview": "Intervjusammanfattning", "after-explore": "Undersök vidare",
    "manager-report": "Chefsrapport"
  } : {
    overview: "Overview", personality: "Personality", motivation: "Motivation",
    cognitive: "Skills", results: "Results",
    interpretation: "AI interpretation", questions: "Interview questions",
    "candidate-reflection": "Candidate reflections",
    "team-report": "Individual team profile",
    "leadership-report": "Leadership report", "derailment-report": "Derailment report",
    "prepare-interview": "Prepare for interview", "after-overview": "Overall picture",
    "after-interview": "Interview summary", "after-explore": "Explore further",
    "manager-report": "Manager report"
  };
  const registry = [
    { id: "overview", selector: "#candidate-insights-panel-overview",
      ready: element => element.textContent.trim().length > 160 },
    ...["personality", "motivation", "cognitive"].flatMap(area =>
      ["results", "interpretation", "questions", "candidate-reflection"].map(part => ({
        id: area + "-" + part, selector: "#" + area + "-subpanel-" + part,
        label: title[area] + " · " + title[part],
        ready: element => {
          if (part === "results" || part === "candidate-reflection")
            return element.textContent.trim().length > 80;
          const result = element.querySelector('[data-has-result="true"]');
          return !!result && !["outdated", "generating"].includes(result.dataset.status)
            && element.textContent.trim().length > 80;
        },
        outdated: element => !!element.querySelector('[data-has-result="true"][data-status="outdated"]')
      }))
    ),
    { id: "team-report", selector: "#reports-subpanel-team-report",
      ready: element => !!element.querySelector(".team-styles-section") },
    { id: "leadership-report", selector: "#reports-subpanel-leadership-report",
      ready: element => !!element.querySelector(".leadership-report__score-overview") },
    { id: "derailment-report", selector: "#reports-subpanel-derailment-report",
      ready: element => !!element.querySelector(".derailment-report__overview") },
    { id: "prepare-interview",
      selector: "#candidate-insights-panel-prepare-interview [data-pre-interview-content]",
      ready: element => !element.classList.contains("d-none") && element.textContent.trim().length > 80 },
    ...[["overview","after-overview"],["explore","after-explore"]]
      .map(([panel, id]) => ({
        id, selector: '[data-after-interview-tab-panel="' + panel + '"] .after-interview-tab-card',
        ready: element => {
          // Helhetsbild has a separate structured renderer (#355), not
          // necessarily the legacy .after-interview-tab-card__body hook.
          if (id === "after-overview") {
            const current = element.querySelector(".after-interview-overall__synthesis");
            const legacy = element.querySelector(".after-interview-overall__legacy .after-interview-tab-card__body");
            return !element.querySelector(".after-interview-overall__source-warning") &&
              (!!current || (!!legacy && legacy.textContent.trim().length > 80));
          }
          const body = element.querySelector(".after-interview-tab-card__body");
          return !!body && !body.classList.contains("after-interview-tab-empty") &&
            body.textContent.trim().length > 80;
        }
      })),
    { id: "manager-report", selector: '[data-after-interview-tab-panel="managerReport"] .after-interview-manager-report',
      existingButton: true, ready: element =>
        !element.hidden && !![...element.querySelectorAll(".after-interview-manager-report__actions button")]
          .find(button => !button.disabled && /pdf/i.test(button.getAttribute("aria-label") || "")) }
  ];
  registry.forEach(item => { item.label ||= title[item.id]; });
  const byId = new Map(registry.map(item => [item.id, item]));
  const getSource = item =>
    workspace && workspace.isConnected !== false
      ? workspace.querySelector(item.selector) : null;
  function isReady(item) {
    const source = getSource(item);
    if (!source) return false;
    try { return Boolean(item.ready(source)); } catch (_) { return false; }
  }
  // #360: first and last name are rendered by Django on the *current*
  // authorised candidate sheet. Do not fall back to the title text, because
  // it may display an email address for candidates without a recorded name.
  function safeFilenamePart(value) {
    return Array.from(String(value || "").normalize("NFC")
      .replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\u2066-\u2069<>:"/\\|?*]/g, " ")
      .replace(/\s+/g, " ")
      .trim()).slice(0, 90).join("").replace(/[.\s-]+$/g, "");
  }
  function candidateExportName() {
    if (!workspace || workspace.isConnected === false ||
        document.querySelector?.("[data-candidate-insights-workspace]") !== workspace) return "";
    const sheet = workspace.closest(".candidate-sheet-layout");
    const identity = sheet?.querySelector(".candidate-profile-name[data-report-export-name]");
    return safeFilenamePart(identity?.getAttribute("data-report-export-name"));
  }
  function reportFilename(item) {
    const name = candidateExportName();
    const reportTitle = safeFilenamePart(item.label.replace(/\s*·\s*/g, " - "));
    return name && reportTitle
      ? name + " - " + reportTitle + ".pdf"
      : "talena-" + item.id + ".pdf";
  }
  function getPackageFilename(format) {
    if (!["pdf", "zip"].includes(format)) throw Error("Unsupported package format");
    const name = candidateExportName();
    const label = format === "zip"
      ? (sv ? "Rapporter" : "Reports")
      : (sv ? "Rapportpaket" : "Report package");
    return name
      ? name + " - " + label + "." + format
      : "talena-" + (format === "zip" ? "rapporter.zip" : "rapportpaket.pdf");
  }
  function getAvailableReports() {
    return registry.filter(isReady).map(item =>
      ({ id: item.id, title: item.label, filename: reportFilename(item) }));
  }
  const create = (tag, css = "", content = null) => {
    const node = document.createElement(tag);
    if (css) node.className = css;
    if (content !== null) node.textContent = content;
    return node;
  };
  function coverFor(item) {
    const branding = workspace.querySelector("[data-final-output-root]")?.dataset || {};
    const primary = /^#[0-9a-f]{6}$/i.test(branding.managerReportBrandPrimary || "")
      ? branding.managerReportBrandPrimary : "#FF6F61";
    const cover = create("div", "talena-team-pdf-cover talena-candidate-pdf-cover");
    cover.style.setProperty("--team-pdf-primary", primary);
    const focus = Number(branding.managerReportBrandFocus);
    cover.style.backgroundPosition = "center " +
      (Number.isFinite(focus) ? Math.min(100, Math.max(0, focus)) : 50) + "%";
    if (branding.managerReportBrandCover) {
      // Use only a trusted, server-rendered branding URL from this page.
      cover.style.backgroundImage = 'linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.72)),url("' +
        branding.managerReportBrandCover.replace(/["\\]/g, "") + '")';
    }
    const brand = create("div", "talena-team-pdf-cover-brand");
    if (branding.managerReportBrandLogo) {
      const logo = create("img");
      logo.src = branding.managerReportBrandLogo;
      logo.alt = "";
      brand.append(logo);
    } else {
      brand.classList.add("talena-team-pdf-cover-brand-fallback");
      brand.textContent = branding.managerReportBrandCompany || "Talena";
    }
    // Only the already visible candidate identity from this exact card may
    // be printed; no query or identifier lookup crosses the current project.
    const candidateName = candidateExportName();
    const caption = create("div", "talena-team-pdf-cover-title");
    caption.append(create("div", "talena-team-pdf-cover-line"),
      create("p", "talena-team-pdf-cover-kicker", "Talena"),
      create("h1", "", item.label),
      create("p", "", candidateName || branding.managerReportBrandCompany || "Talena"));
    cover.append(brand, caption);
    return cover;
  }
  function copyContent(source) {
    const clone = source.cloneNode(true);
    clone.removeAttribute("hidden");
    clone.classList.remove("d-none");
    clone.style.display = "block";
    const liveCanvases = source.querySelectorAll("canvas");
    clone.querySelectorAll("canvas").forEach((canvas, index) => {
      // Inactive optional panels are removed below. They must not block
      // export just because their hidden canvases were never rendered.
      if (canvas.closest('[hidden], .d-none')) return;
      const live = liveCanvases[index];
      if (!live || !live.width || !live.height) throw Error("Chart not ready");
      const image = create("img", "talena-candidate-pdf-chart");
      image.src = live.toDataURL("image/png");
      canvas.replaceWith(image);
    });
    clone.querySelectorAll("details").forEach(details => { details.open = true; });
    // aria-hidden is an accessibility attribute, NOT a CSS visibility rule.
    // The personality indicator's decorative centre-line has aria-hidden=true
    // yet occupies the middle column of a 3-column chart grid. Removing it
    // collapses the right-hand five STEN steps into a one-pixel column.
    // Preserve visible decorative layout nodes; strip aria-* attributes below.
    clone.querySelectorAll(
      'button, form, input, textarea, select, script, iframe, video, audio, ' +
      '[data-candidate-pdf-toolbar], .modal, .offcanvas, [hidden], .d-none, [contenteditable]'
    ).forEach(element => element.remove());
    clone.querySelectorAll("a").forEach(link => {
      const plain = create("span", link.className, link.textContent || "");
      link.replaceWith(plain);
    });
    [clone, ...clone.querySelectorAll("*")].forEach(node => {
      [...node.attributes].forEach(attribute => {
        if (attribute.name.startsWith("data-") || attribute.name.startsWith("on") ||
          attribute.name.startsWith("aria-") ||
          ["href","title","for"].includes(attribute.name) ||
          // SVG ids may be referenced by chart fills, clips or markers.
          (attribute.name === "id" && node.namespaceURI !== "http://www.w3.org/2000/svg"))
          node.removeAttribute(attribute.name);
      });
    });
    return clone;
  }

  let exporting = false;
  async function exportReport(id, options = {}) {
    const item = byId.get(id);
    if (!item || !isReady(item)) throw Error(copy.unavailable);
    if (exporting) throw Error(copy.busy);
    if (!window.TalenaPdfExport?.exportSections) throw Error(copy.error);
    const downloadName = reportFilename(item); // freeze identity before async work
    exporting = true;
    let stage;
    try {
      let managerReportMetadata = null;
      const reportContent = copyContent(getSource(item));
      if (id === "manager-report") {
        if (!window.TalenaManagerReportPdf) throw Error(copy.error);
        managerReportMetadata = await window.TalenaManagerReportPdf.prepare(workspace);
        window.TalenaManagerReportPdf.decorate(reportContent, managerReportMetadata);
      }
      const body = create("main", "talena-candidate-pdf-body candidate-insight-page");
      body.append(create("h1", "talena-candidate-pdf-heading", item.label),
        reportContent);
      const cover = coverFor(item);
      stage = create("div", "process-page candidate-insights-workspace talena-candidate-pdf-stage");
      stage.setAttribute("data-candidate-pdf-report", item.id);
      stage.append(cover, body);
      document.body.append(stage);
      await new Promise(resolve => requestAnimationFrame(resolve));
      const blob = await window.TalenaPdfExport.exportSections(
        [{node:cover, cover:true}, {node:body, continuous:true}],
        {title:item.label, subject:item.label, returnBlob:true}
      );
      if (managerReportMetadata) {
        try {
          await window.TalenaManagerReportPdf.recordGenerated(workspace, managerReportMetadata);
        } catch (_auditError) {
          // The PDF blob exists. Do not turn a logging error into a broken export.
          console.warn("Manager report PDF generation audit could not be recorded.");
        }
      }
      if (options.returnBlob) return blob; // #360 consumes the exact same PDF Blob.
      const url = URL.createObjectURL(blob);
      const link = create("a");
      try {
        link.href = url;
        link.download = downloadName;
        document.body.append(link);
        link.click();
        link.remove();
      } finally {
        window.setTimeout(() => URL.revokeObjectURL(url), 30000);
      }
      return blob;
    } finally {
      stage?.remove();
      exporting = false;
    }
  }
  // #360: brand the merged file with the same existing cover used for every
  // single-report export. No candidate data leaves this page.
  async function exportCover(label) {
    if (!workspace?.isConnected || !window.TalenaPdfExport?.exportSections)
      throw Error(copy.unavailable);
    const title = String(label || "Talena").slice(0, 100);
    const cover = coverFor({label:title});
    const stage = create("div", "process-page candidate-insights-workspace talena-candidate-pdf-stage");
    stage.append(cover);
    document.body.append(stage);
    try {
      await new Promise(resolve => requestAnimationFrame(resolve));
      return await window.TalenaPdfExport.exportSections(
        [{node:cover, cover:true}], {title,subject:title,returnBlob:true}
      );
    } finally {
      stage.remove();
    }
  }
  // Shared icon: native title/ARIA work even before Feather initialises an
  // AJAX-loaded candidate sheet. This is intentionally not a text-sized CTA.
  const pdfIcon = '<svg width="19" height="19" viewBox="0 0 24 24" ' +
    'fill="none" stroke="currentColor" stroke-width="1.75" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>' +
    '<polyline points="14 2 14 8 20 8"/>' +
    '<path d="M12 12v6m-3-3 3 3 3-3"/></svg>';

  // Every download lives inside the heading/action row, rather than in a
  // standalone top-of-panel row. Keep the native generate button and its
  // listeners intact; only move it into a shared pair with the PDF action.
  const generateSelector = [
    ".js-regenerate-purpose-fit",
    "[data-personality-ai-regenerate]",
    "[data-personality-questions-regenerate]",
    "[data-motivation-ai-regenerate]",
    "[data-motivation-questions-regenerate]",
    "[data-cognitive-interpretation-regenerate]",
    "[data-cognitive-questions-regenerate]",
    "[data-pre-interview-generate][data-regenerate='true']",
    "[data-post-interview-generate][data-regenerate='true']",
    // After interview's individual report cards have their own refresh
    // buttons inside the title toolbar. Pair the PDF export with that
    // existing action instead of inserting a separate row above the card.
    "[data-after-interview-regenerate]",
    // Helhetsbild's structured card has its own refresh action.
    // Pair the existing PDF control with it instead of creating a toolbar row.
    "[data-overall-picture-generate]"
  ].join(", ");

  function findHeading(source) {
    return source.querySelector(
      ".response-styles-header, .team-styles-header, " +
      ".personality-questions-header, .team-report__page-header, " +
      ".leadership-report__page-header, .derailment-report__page-header, " +
      ".candidate-insight-page-header"
    );
  }

  function placeToolbar(source, item, toolbar) {
    const generate = source.querySelector(generateSelector);
    const actions = item.id === "overview"
      ? source.querySelector(".ai-overview-header__actions")
      : generate?.parentElement;
    // Overview now reuses existing interpretations and has no Generate action.
    // Keep its PDF control in the existing header action area.
    if (item.id === "overview" && actions && !generate) {
      actions.append(toolbar);
      toolbar.classList.add("talena-candidate-pdf-toolbar--inline", "talena-candidate-pdf-toolbar--overview");
      return;
    }
    if (actions && generate) {
      if (item.id === "overview") {
        toolbar.classList.add("talena-candidate-pdf-toolbar--overview");
      }
      const pair = create("div", "talena-candidate-report-button-pair");
      const parent = generate.parentNode;
      parent.insertBefore(pair, generate);
      pair.append(toolbar, generate);
      generate.classList.add("talena-report-action-button");
      toolbar.classList.add("talena-candidate-pdf-toolbar--inline");
      return;
    }
    // A results-only tab has no Generate control. Reuse its existing
    // heading rather than creating a 42px action row above the heading.
    const header = findHeading(source);
    if (header) {
      header.classList.add("talena-candidate-report-heading-row");
      if (header.classList.contains("team-styles-header") &&
          !header.querySelector(".talena-candidate-report-heading")) {
        // This header has two direct text blocks (h2 + description).
        const heading = create("div", "talena-candidate-report-heading");
        while (header.firstChild) heading.append(header.firstChild);
        header.append(heading);
      }
      header.append(toolbar);
      toolbar.classList.add("talena-candidate-pdf-toolbar--inline");
      return;
    }
    // Some report fragments have no heading or Generate action yet.
    toolbar.classList.add("talena-candidate-pdf-toolbar--standalone");
    source.insertBefore(toolbar, source.firstChild);
  }

  function addToolbar(item) {
    if (item.existingButton) return; // Chefsrapport keeps its own PDF button.
    const source = getSource(item);
    if (!source || source.querySelector("[data-candidate-pdf-toolbar]")) return;
    const toolbar = create("div", "talena-candidate-pdf-toolbar");
    toolbar.setAttribute("data-candidate-pdf-toolbar", "");
    const button = create("button",
      "btn btn-icon btn-light talena-candidate-pdf-button talena-report-action-button");
    button.type = "button";
    button.innerHTML = pdfIcon;
    button.setAttribute("aria-label", copy.action);
    button.title = copy.action;
    const message = create("span", "talena-candidate-pdf-message");
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");
    toolbar.append(button, message);
    placeToolbar(source, item, toolbar);

    button.addEventListener("click", async () => {
      if (button.disabled || exporting) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.classList.add("is-loading");
      message.textContent = "";
      message.classList.remove("is-error");
      try {
        await exportReport(item.id);
        message.textContent = copy.success;
      } catch (_) {
        message.textContent = copy.error;
        message.classList.add("is-error");
      } finally {
        button.disabled = !isReady(item);
        button.removeAttribute("aria-busy");
        button.classList.remove("is-loading");
      }
    });
  }
  function refresh() {
    queued = false;
    registry.forEach(item => {
      addToolbar(item);
      const toolbar = getSource(item)?.querySelector("[data-candidate-pdf-toolbar]");
      if (!toolbar) return;
      const button = toolbar.querySelector("button");
      const status = toolbar.querySelector('[role="status"]');
      const ready = isReady(item);
      if (!exporting) button.disabled = !ready;
      const unavailable = item.outdated?.(getSource(item)) ? copy.outdated : copy.unavailable;
      button.title = ready ? copy.action : unavailable;
      button.setAttribute("aria-label", button.title);
      if (!status) return;
      if (!ready && !status.textContent.trim())
        status.textContent = item.outdated?.(getSource(item)) ? copy.outdated : copy.unavailable;
      if (ready && [copy.unavailable, copy.outdated].includes(status.textContent.trim()))
        status.textContent = "";
    });
  }
  let queued = false;
  const schedule = () => {
    if (queued) return;
    queued = true;
    Promise.resolve().then(refresh);
  };
  function initialize(container = document) {
    const current = container.querySelector?.("[data-candidate-insights-workspace]") ||
      (container.matches?.("[data-candidate-insights-workspace]") ? container : null);
    if (!current) return;
    if (workspace === current) {
      schedule();
      window.TalenaReportPackages?.initialize?.(current);
      return;
    }
    // A different candidate replaces the offcanvas body. Stop observing the
    // previous candidate to prevent stale UI updates and cross-candidate reads.
    observer?.disconnect();
    workspace = current;
    observer = new MutationObserver(schedule);
    observer.observe(workspace, {
      subtree:true, childList:true, characterData:true,
      attributes:true, attributeFilter:["class","hidden","data-has-result","data-status"]
    });
    schedule();
    window.TalenaReportPackages?.initialize?.(current);
  }
  window.TalenaCandidateReports = Object.freeze({
    initialize, getAvailableReports, exportReport, exportCover, getPackageFilename
  });
  initialize(document); // Also supports pages where the sheet is already in the DOM.
})();
