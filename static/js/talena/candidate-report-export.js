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
    ...[["overview","after-overview"],["interview","after-interview"],["explore","after-explore"]]
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
  function getAvailableReports() {
    return registry.filter(isReady).map(item =>
      ({ id: item.id, title: item.label, filename: "talena-" + item.id + ".pdf" }));
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
    const candidateName = workspace.closest(".candidate-sheet-layout")
      ?.querySelector(".candidate-profile-name")?.textContent.trim() || "";
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
    clone.querySelectorAll(
      'button, form, input, textarea, select, script, iframe, video, audio, ' +
      '[data-candidate-pdf-toolbar], .modal, .offcanvas, [hidden], .d-none, [aria-hidden="true"], [contenteditable]'
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
    exporting = true;
    let stage;
    try {
      const body = create("main", "talena-candidate-pdf-body");
      body.append(create("h1", "talena-candidate-pdf-heading", item.label),
        copyContent(getSource(item)));
      const cover = coverFor(item);
      stage = create("div", "process-page candidate-insights-workspace talena-candidate-pdf-stage");
      stage.append(cover, body);
      document.body.append(stage);
      await new Promise(resolve => requestAnimationFrame(resolve));
      const blob = await window.TalenaPdfExport.exportSections(
        [{node:cover, cover:true}, {node:body, continuous:true}],
        {title:item.label, subject:item.label, returnBlob:true}
      );
      if (options.returnBlob) return blob; // #360 consumes the exact same PDF Blob.
      const url = URL.createObjectURL(blob);
      const link = create("a");
      try {
        link.href = url;
        link.download = "talena-" + item.id + ".pdf";
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
  function addToolbar(item) {
    if (item.existingButton) return; // Chefsrapport has its own download button.
    const source = getSource(item);
    if (!source || source.querySelector(":scope > [data-candidate-pdf-toolbar]")) return;
    const toolbar = create("div", "talena-candidate-pdf-toolbar");
    toolbar.setAttribute("data-candidate-pdf-toolbar", "");
    const button = create("button", "btn btn-outline-primary btn-sm", copy.action);
    button.type = "button";
    const message = create("span", "talena-candidate-pdf-message");
    message.setAttribute("role", "status");
    message.setAttribute("aria-live", "polite");
    toolbar.append(button, message);
    source.insertBefore(toolbar, source.firstChild);
    button.addEventListener("click", async () => {
      if (button.disabled || exporting) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.textContent = copy.busy;
      message.textContent = "";
      try {
        await exportReport(item.id);
        message.textContent = copy.success;
      } catch (_) {
        message.textContent = copy.error;
      } finally {
        button.disabled = !isReady(item);
        button.removeAttribute("aria-busy");
        button.textContent = copy.action;
      }
    });
  }
  function refresh() {
    queued = false;
    registry.forEach(item => {
      addToolbar(item);
      const toolbar = getSource(item)?.querySelector(":scope > [data-candidate-pdf-toolbar]");
      if (!toolbar) return;
      const button = toolbar.querySelector("button");
      const status = toolbar.querySelector('[role="status"]');
      const ready = isReady(item);
      if (!exporting) button.disabled = !ready;
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
  }
  window.TalenaCandidateReports = Object.freeze({
    initialize, getAvailableReports, exportReport
  });
  initialize(document); // Also supports pages where the sheet is already in the DOM.
})();
