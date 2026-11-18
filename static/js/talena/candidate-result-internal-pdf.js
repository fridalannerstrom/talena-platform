/* #475: Download the candidate-facing static report from its authorised preview.
   This runs in the user's browser using Talena's existing PDF engine. It never
   creates a public result link, submits feedback, or sends an email. */
(function () {
  "use strict";
  if (window.TalenaInternalCandidateReportPdf) return;

  const copy = {
    sv: {
      busy: "Skapar PDF…",
      error: "PDF-rapporten kunde inte skapas. Prova igen.",
    },
    en: {
      busy: "Creating PDF…",
      error: "The PDF report could not be created. Try again.",
    },
  };
  const language = document.documentElement.lang.toLowerCase().startsWith("sv") ? "sv" : "en";
  let exporting = false;

  const safeName = (value) => String(value || "")
    .normalize("NFKC")
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 70) || "Kandidat";

  async function download() {
    if (exporting) return false;
    const root = document.querySelector("[data-candidate-result-internal-preview]");
    if (!root || !window.TalenaPdfExport?.exportSections) {
      throw new Error(copy[language].error);
    }

    const candidate = root.querySelector(".hero-title-row h1")?.textContent?.trim();
    const filename = "Talena - Kandidatrapport - " + safeName(candidate) + ".pdf";
    const stage = root.cloneNode(true);
    stage.removeAttribute("data-candidate-result-internal-preview");
    stage.querySelectorAll(".preview-banner, .candidate-result-pdf-toolbar, .feedback-block, .feedback-dialog, #test-experience")
      .forEach(node => node.remove());
    // The shared PDF engine knows where to break .card sections. Add that
    // marker to the export clone only, keeping headings and content together.
    stage.querySelectorAll(".hero-card, .intro-card, .section-card")
      .forEach(node => node.classList.add("card"));
    // html2canvas captures a real, styled DOM clone without altering the
    // report on screen. Do not capture the preview badge or download controls.
    stage.style.cssText = "position:fixed;top:0;left:-10000px;width:794px;max-width:none;padding:20px;background:#fff;z-index:-1;pointer-events:none;";
    exporting = true;
    document.body.appendChild(stage);
    try {
      await new Promise(resolve => window.requestAnimationFrame(resolve));
      await window.TalenaPdfExport.exportSections(
        [{ node: stage, continuous: true }],
        {
          title: "Kandidatrapport - " + (candidate || "Talena"),
          subject: "Candidate assessment results",
          filename,
        }
      );
      void window.TalenaReportExportActivity?.record?.(
        root.dataset?.reportExportReceiptUrl, "candidate-static-report"
      );
      return true;
    } finally {
      stage.remove();
      exporting = false;
    }
  }

  // The customer candidate tab contains a same-origin preview iframe.
  // Download straight from there when loaded; otherwise open the protected
  // preview with its own dedicated PDF button as the safe fallback.
  document.addEventListener("click", event => {
    const link = event.target.closest?.("[data-candidate-result-download]");
    if (!link || event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const iframe = link.closest(".candidate-result-report-panel")
      ?.querySelector(".candidate-result-report-frame");
    let downloader = null;
    try {
      downloader = iframe?.contentWindow?.TalenaInternalCandidateReportPdf?.download;
    } catch (_error) {
      // Cross-origin or not-yet-loaded frames use the protected preview link.
    }
    if (typeof downloader !== "function") return;
    event.preventDefault();
    if (link.getAttribute("aria-busy") === "true") return;
    link.setAttribute("aria-busy", "true");
    link.classList.add("disabled");
    Promise.resolve().then(() => downloader()).catch(() => {
      window.alert(copy[language].error);
    }).finally(() => {
      link.removeAttribute("aria-busy");
      link.classList.remove("disabled");
    });
  });

  document.addEventListener("click", event => {
    const button = event.target.closest?.("[data-candidate-result-pdf-button]");
    if (!button || button.disabled) return;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    const label = button.querySelector("[data-candidate-result-pdf-label]");
    const original = label?.textContent || "";
    const error = document.querySelector("[data-candidate-result-pdf-error]");
    if (label) label.textContent = copy[language].busy;
    if (error) {
      error.hidden = true;
      error.textContent = "";
    }
    download().catch(() => {
      if (error) {
        error.textContent = copy[language].error;
        error.hidden = false;
      }
    }).finally(() => {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      if (label) label.textContent = original;
    });
  });

  window.TalenaInternalCandidateReportPdf = Object.freeze({ download });
})();
