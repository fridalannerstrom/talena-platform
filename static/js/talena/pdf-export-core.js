/* Shared PDF raster-page engine for Talena report exports.
   Works entirely in the authorized browser page; no AI calls or PDF uploads. */
(function () {
  "use strict";
  if (window.TalenaPdfExport) return;
  let librariesPromise = null;

  function loadScript(id, url, isReady) {
    if (isReady()) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      const existing = document.getElementById(id);
      const script = existing || document.createElement("script");
      if (!existing) {
        script.id = id;
        script.src = url;
        script.crossOrigin = "anonymous";
        script.referrerPolicy = "no-referrer";
      }
      const fail = () => reject(new Error("The PDF library could not be loaded."));
      script.addEventListener("load", () => isReady() ? resolve() : fail(), { once: true });
      script.addEventListener("error", fail, { once: true });
      if (!existing) document.head.appendChild(script);
    });
  }

  function ensureLibraries() {
    if (!librariesPromise) {
      librariesPromise = Promise.all([
        loadScript(
          "talena-team-html2canvas",
          "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
          () => typeof window.html2canvas === "function"
        ),
        loadScript(
          "talena-team-jspdf",
          "https://cdnjs.cloudflare.com/ajax/libs/jspdf/4.2.1/jspdf.umd.min.js",
          () => typeof window.jspdf?.jsPDF === "function"
        )
      ]).catch(err => {
        librariesPromise = null;
        throw err;
      });
    }
    return librariesPromise;
  }

  async function capture(node) {
    if (!node) throw new Error("The report section is unavailable.");
    if (document.fonts?.ready) await document.fonts.ready;
    const imgs = Array.from(node.querySelectorAll("img"));
    await Promise.all(imgs.map(img => {
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {
        img.addEventListener("load", resolve, { once: true });
        img.addEventListener("error", resolve, { once: true });
      });
    }));
    return window.html2canvas(node, {
      backgroundColor: "#ffffff",
      scale: 1.6,
      useCORS: true,
      logging: false,
      scrollX: 0, scrollY: 0,
      windowWidth: Math.max(960, document.documentElement.clientWidth)
    });
  }

  function calculatePageSlices(totalHeight, maxHeight, boundaries, protectedRanges = []) {
    // Existing report types retain their original 72%-filled natural breaks.
    // The optional protected ranges are used by Motivation only. A card's
    // heading, description and complete five-point scale must stay together.
    const slices = [];
    const safeHeight = Math.max(1, Math.floor(maxHeight));
    const ranges = (protectedRanges || [])
      .filter(range => Number.isFinite(range.start) && Number.isFinite(range.end))
      .map(range => ({
        start: Math.max(0, Math.round(range.start)),
        end: Math.min(totalHeight, Math.round(range.end))
      }))
      .filter(range => range.end > range.start);
    const points = Array.from(new Set([
      ...(boundaries || []),
      ...ranges.flatMap(range => [range.start, range.end])
    ].filter(y => Number.isFinite(y) && y > 0 && y < totalHeight)
      .map(Math.round))).sort((a, b) => a - b);
    const protectedInside = y =>
      ranges.some(range => y > range.start && y < range.end);
    let offset = 0;
    while (offset < totalHeight) {
      const limit = Math.min(offset + safeHeight, totalHeight);
      let next = limit;
      if (limit < totalHeight) {
        const crossesCard = protectedInside(limit);
        const candidates = points.filter(y =>
          y > offset && y <= limit && !protectedInside(y)
        );
        if (crossesCard) {
          // Never end inside a protected Motivation card when it can fit on
          // the next page. Prefer its start, even below the usual 72% fill.
          // A card taller than one page still uses the fallback below.
          const safe = candidates.filter(y => y >= offset + safeHeight * 0.18);
          if (safe.length) next = safe[safe.length - 1];
        } else {
          const minimumFill = offset + safeHeight * 0.72;
          const nearBottom = candidates.filter(y => y >= minimumFill);
          if (nearBottom.length) next = nearBottom[nearBottom.length - 1];
        }
      }
      if (next <= offset) next = limit; // Oversized content must make progress.
      slices.push({ start: offset, height: next - offset });
      offset = next;
    }
    return slices;
  }

  function getNaturalBreaks(node, source) {
    if (!node || !node.getBoundingClientRect) return [];
    const box = node.getBoundingClientRect();
    if (!box.width) return [];
    const scale = source.width / box.width;
    const candidates = node.querySelectorAll(
      ".team-report-pdf-part, .team-summary-item, .team-analytics-panel, " +
      ".team-insight-card, .team-style-rank-row, .team-style-rank-list, " +
      ".team-analytics-grid, .team-table tr, .card, .card-body, .team-goal-list, " +
      ".team-style-profile-card, .team-styles-section, .team-profile-pdf-heading, " +
      ".after-interview-manager-report__skill, .after-interview-manager-report__guide-level, " +
      ".after-interview-manager-report__motivator, .after-interview-manager-report__motivator-practical-box, " +
      ".after-interview-manager-report__personality-theme, .after-interview-manager-report__personality-part, " +
      ".after-interview-manager-report__personality-advice, .after-interview-manager-report__wellbeing, " +
      ".after-interview-manager-report__interview-comments, .after-interview-manager-report__intro-paragraph, " +
      ".after-interview-manager-report__section-intro, .after-interview-manager-report__motivator-name, " +
      ".after-interview-manager-report__motivation-title, .after-interview-manager-report__skills-title, " +
      ".after-interview-manager-report__personality-title, .after-interview-manager-report__guide-summary, " +
      ".after-interview-manager-report__wellbeing-title, " +
      // Trait cards may be taller than a page, so rows and summaries must
      // also be possible breakpoints. Never split an indicator's text/scale.
      ".personality-profile-section__header, .personality-trait-card__header, " +
      ".personality-trait-card__main, .personality-trait-card__summary, " +
      ".personality-indicator-row, .personality-trait-card, .personality-quick-row, " +
      ".personality-description-quick-row, " +
      ".personality-overview-group, .personality-overview-item, " +
      ".candidate-result-overview__area, .candidate-result-overview__personality, " +
      ".candidate-result-overview__motivation-card, .candidate-result-overview__skill-card"
    );
    const points = [];
    candidates.forEach(element => {
      const rect = element.getBoundingClientRect();
      if (!rect.height) return;
      const bottom = Math.round((rect.bottom - box.top) * scale);
      if (bottom > 0 && bottom < source.height) points.push(bottom);
      // A section can start near a page edge even if its bottom lies on the
      // next page. Its top is a valid boundary before that section, too.
      // Avoid top/bottom duplicates for near-zero-height elements.
      const top = Math.round((rect.top - box.top) * scale);
      if (rect.height > 12 && top > 0 && top < source.height) points.push(top);
    });
    return points;
  }

  function getMotivationPageGuides(node, source) {
    // Work in raster pixels, matching html2canvas. In the normal DOM the
    // same content remains fully interactive; this runs on the PDF clone.
    const box = node.getBoundingClientRect();
    if (!box.width) return [];
    const pixelsPerCssPx = source.width / box.width;
    const guides = [];
    function protect(startElement, endElement = startElement) {
      if (!startElement || !endElement) return;
      const startBox = startElement.getBoundingClientRect();
      const endBox = endElement.getBoundingClientRect();
      if (!startBox.height || !endBox.height) return;
      const start = Math.round((startBox.top - box.top) * pixelsPerCssPx);
      const end = Math.round((endBox.bottom - box.top) * pixelsPerCssPx);
      if (end > start && end > 0 && start < source.height) {
        guides.push({ start: Math.max(0, start), end: Math.min(source.height, end) });
      }
    }

    node.querySelectorAll(
      ".motivation-visual-overview, .motivation-summary-item, " +
      ".motivation-factor-result, .motivation-profile-footer"
    ).forEach(item => protect(item));

    // A heading followed by its first card is one logical unit. This stops
    // 'All motivation factors' and the prominent/least-prominent headings
    // from being orphaned at the bottom of a PDF page.
    node.querySelectorAll(".motivation-summary-list").forEach(list => {
      const first = list.querySelector(".motivation-summary-item");
      const header = list.closest("article")?.querySelector(
        ".response-style-item__header"
      );
      protect(header, first);
    });
    protect(
      node.querySelector(".motivation-full-profile-heading"),
      node.querySelector(".motivation-factor-list .motivation-factor-result")
    );
    return guides;
  }

  function getMotivationQuestionsPageGuides(node, source) {
    const container = node.getBoundingClientRect();
    if (!container.width) return [];
    const scale = source.width / container.width;
    const ranges = [];
    function protect(first, last = first) {
      if (!first || !last) return;
      const startBox = first.getBoundingClientRect();
      const endBox = last.getBoundingClientRect();
      if (!startBox.height || !endBox.height) return;
      const start = Math.max(0, Math.round((startBox.top - container.top) * scale));
      const end = Math.min(source.height,
        Math.round((endBox.bottom - container.top) * scale));
      if (end > start) ranges.push({ start, end });
    }
    // Each full question includes its header, Why this matters and
    // What to look for. Never cut it between PDF pages if it fits on one.
    node.querySelectorAll(
      ".interview-section-guidance, .interview-static-questions, " +
      ".personality-question-card, .purpose-fit-disclaimer, " +
      ".personality-questions-traits, .personality-questions-context-note"
    ).forEach(section => protect(section));

    // A subsection title must travel with at least its first question.
    protect(
      node.querySelector(".personality-questions-header"),
      node.querySelector(".personality-question-card")
    );
    return ranges;
  }

  function getCognitiveResultsPageGuides(node, source) {
    // In the percentile guide every level's label, meaning and bullet
    // list is a single printable unit. The guide as a whole spans pages.
    const container = node.getBoundingClientRect();
    if (!container.width) return [];
    const scale = source.width / container.width;
    const ranges = [];
    function protect(first, last = first) {
      if (!first || !last) return;
      const from = first.getBoundingClientRect();
      const to = last.getBoundingClientRect();
      if (!from.height || !to.height) return;
      const start = Math.max(0, Math.round(
        (from.top - container.top) * scale
      ));
      const end = Math.min(source.height, Math.round(
        (to.bottom - container.top) * scale
      ));
      if (end > start) ranges.push({ start, end });
    }
    node.querySelectorAll(".cognitive-result-card")
      .forEach(card => protect(card));
    node.querySelectorAll(".cognitive-percentile-guide__level")
      .forEach(level => protect(level));
    // Prevent an orphaned "How to interpret percentiles" heading.
    protect(
      node.querySelector(".cognitive-percentile-guide > summary"),
      node.querySelector(".cognitive-percentile-guide__level")
    );
    node.querySelectorAll(
      ".cognitive-percentile-guide__intro, .cognitive-percentile-guide + .small"
    ).forEach(section => protect(section));
    return ranges;
  }

  function getPersonalityResultsPageGuides(node, source, maxHeight) {
    // Character traits form long continuous reports. Keep the opening
    // (name, main score graph, interpretation and first indicator) together
    // whenever it fits on A4; do not try to put the *entire* trait on a
    // single page, which would waste space or force arbitrary cuts.
    const container = node.getBoundingClientRect();
    if (!container.width) return [];
    const scale = source.width / container.width;
    const ranges = [];

    function protect(first, last = first, maxFraction = 1) {
      if (!first || !last) return;
      const from = first.getBoundingClientRect();
      const to = last.getBoundingClientRect();
      if (!from.height || !to.height) return;
      const start = Math.max(0, Math.round((from.top - container.top) * scale));
      const end = Math.min(source.height,
        Math.round((to.bottom - container.top) * scale));
      // A group that is taller than a printable page must be allowed to
      // break at its internal indicator boundaries.
      if (end > start && end - start <= maxHeight * maxFraction) {
        ranges.push({ start, end });
      }
    }

    node.querySelectorAll(".personality-profile-section").forEach(section => {
      const title = section.querySelector(".personality-profile-section__header");
      const firstTrait = section.querySelector(".personality-trait-card");
      const introEnd = firstTrait?.querySelector(
        ".personality-trait-card__summary, .personality-trait-card__main"
      );
      // A category heading should never be left alone at the foot of a
      // page without the first personality trait and its graph.
      protect(title, introEnd, 0.78);
    });

    node.querySelectorAll(".personality-trait-card").forEach(trait => {
      const heading = trait.querySelector(".personality-trait-card__header");
      const main = trait.querySelector(".personality-trait-card__main");
      const summary = trait.querySelector(".personality-trait-card__summary");
      const firstIndicator = trait.querySelector(".personality-indicator-row");
      // First try to include the first indicator; if the opening is too
      // tall, still keep the title, score graph and summary together.
      const introEnd = summary || main || heading;
      const startCount = ranges.length;
      protect(heading, firstIndicator || introEnd, 0.75);
      if (ranges.length === startCount) protect(heading, introEnd, 0.75);
      // Indicator names, two pole descriptions and the complete STEN
      // scale must never be separated by a PDF page edge.
      trait.querySelectorAll(".personality-indicator-row").forEach(row => {
        protect(row);
      });
    });
    return ranges;
  }

  function getPersonalityQuickPageGuides(node, source, maxHeight) {
    // The trait-only profile is shorter than the detailed indicator report.
    // Keep its three six-trait sections together when a complete section
    // fits on the sheet, avoiding orphan category headers on the prior page.
    const container = node.getBoundingClientRect();
    if (!container.width) return [];
    const scale = source.width / container.width;
    const ranges = [];
    const root = node.querySelector(".personality-quick-view");
    if (!root) return ranges;

    function protect(element, endElement = element, maxFraction = 1) {
      if (!element || !endElement) return;
      const from = element.getBoundingClientRect();
      const to = endElement.getBoundingClientRect();
      if (!from.height || !to.height) return;
      const start = Math.max(0, Math.round((from.top - container.top) * scale));
      const end = Math.min(source.height,
        Math.round((to.bottom - container.top) * scale));
      // Longer sections fall back to whole rows rather than forcing
      // impossible one-page blocks or leaving huge blank page areas.
      if (end > start && end - start <= maxHeight * maxFraction) {
        ranges.push({ start, end });
      }
    }

    const overview = root.querySelector(".personality-overview-chart");
    protect(overview, overview, 0.95);
    root.querySelectorAll(".personality-quick-section").forEach(section => {
      protect(section, section, 0.9);
      const title = section.querySelector(".personality-quick-section__header");
      const firstRow = section.querySelector(".personality-quick-row");
      protect(title, firstRow, 0.78);
      section.querySelectorAll(".personality-quick-row")
        .forEach(row => protect(row));
    });
    return ranges;
  }

  function getPersonalityDescriptionPageGuides(node, source, maxHeight) {
    // The 18 text-only personality results are neither the detailed
    // indicator view nor the segmented quick view. Protect complete
    // heading+description rows so their copy is never cut in half.
    const container = node.getBoundingClientRect();
    if (!container.width) return [];
    const scale = source.width / container.width;
    const ranges = [];
    const descriptions = node.querySelector(".personality-trait-descriptions-view");
    if (!descriptions) return ranges;

    function protect(startNode, endNode = startNode) {
      if (!startNode || !endNode) return;
      const startBox = startNode.getBoundingClientRect();
      const endBox = endNode.getBoundingClientRect();
      if (!startBox.height || !endBox.height) return;
      const start = Math.max(0, Math.round((startBox.top - container.top) * scale));
      const end = Math.min(source.height,
        Math.round((endBox.bottom - container.top) * scale));
      // A particularly long translated description might exceed one page.
      // In that case keep pagination moving rather than looping.
      if (end > start && end - start <= maxHeight) ranges.push({ start, end });
    }

    descriptions.querySelectorAll(".personality-description-section").forEach(section => {
      const heading = section.querySelector(".personality-quick-section__header");
      const firstRow = section.querySelector(".personality-description-quick-row");
      // Section headings must appear with at least the first trait.
      protect(heading, firstRow);
      // Do not keep whole six-trait sections together: they can easily
      // exceed one page and would leave needlessly empty pages.
      section.querySelectorAll(".personality-description-quick-row").forEach(row => {
        protect(row);
      });
    });
    return ranges;
  }

  function getManagerReportPageGuides(node, source, maxHeight) {
    // The manager report is a single browser-rasterized long page. CSS
    // break-inside alone cannot protect its content from canvas slicing.
    // Convert logical units into pixel ranges for the actual A4 page cutter.
    const rect = node.getBoundingClientRect();
    if (!rect.width) return [];
    const scale = source.width / rect.width;
    const protectedRanges = [];

    function protect(startNode, endNode = startNode, maxPageFraction = 0.95) {
      if (!startNode || !endNode) return;
      const startRect = startNode.getBoundingClientRect();
      const endRect = endNode.getBoundingClientRect();
      if (!startRect.height || !endRect.height) return;
      const start = Math.max(0, Math.round((startRect.top - rect.top) * scale));
      const end = Math.min(source.height, Math.round((endRect.bottom - rect.top) * scale));
      // Over-height content must break inside; it cannot be protected as a
      // whole without leading to blank pages or unbounded pagination.
      if (end > start && end - start <= maxHeight * maxPageFraction) {
        protectedRanges.push({ start, end });
      }
    }

    node.querySelectorAll(
      ".after-interview-manager-report__skill, " +
      ".after-interview-manager-report__motivator, " +
      ".after-interview-manager-report__interview-comments, " +
      ".after-interview-manager-report__personality-theme, " +
      ".after-interview-manager-report__guide-level"
    ).forEach(section => protect(section));

    node.querySelectorAll(
      ".after-interview-manager-report__motivator-practical-box, " +
      ".after-interview-manager-report__intro-paragraph, " +
      ".after-interview-manager-report__wellbeing .after-interview-rich-text__paragraph, " +
      ".after-interview-manager-report__wellbeing .after-interview-rich-text__list"
    ).forEach(section => protect(section));

    // Keep each heading with an intro / first substantive card if it fits.
    [
      [".after-interview-manager-report__skills-title",
       ".after-interview-manager-report__skill"],
      [".after-interview-manager-report__motivation-title",
       ".after-interview-manager-report__motivator"],
      [".after-interview-manager-report__personality-title",
       ".after-interview-manager-report__personality-theme"],
      [".after-interview-manager-report__wellbeing-title",
       ".after-interview-manager-report__wellbeing .after-interview-rich-text__paragraph"],
      [".after-interview-manager-report__guide-summary",
       ".after-interview-manager-report__guide-level"],
    ].forEach(([heading, firstCard]) => {
      protect(node.querySelector(heading), node.querySelector(firstCard), 0.75);
    });

    return protectedRanges;
  }

  function addCanvasPages(pdf, source, opts) {
    if (!source.width || !source.height) throw new Error("PDF page is empty.");
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = opts.cover ? 0 : 12;
    const width = pageW - margin * 2;
    const height = pageH - margin * 2;
    const pixelsPerMm = source.width / width;
    const maxHeight = Math.max(1, Math.floor(height * pixelsPerMm));
    const breakpoints = opts.continuous ? getNaturalBreaks(opts.node, source) : [];
    const motivationPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="motivation-results"]');
    const motivationQuestionsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="motivation-questions"]');
    const cognitiveQuestionsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="cognitive-questions"]');
    const personalityQuestionsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="personality-questions"]');
    const combinedInterviewQuestionsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="combined-interview-questions"]');
    const cognitiveResultsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="cognitive-results"]');
    const personalityResultsPdf = opts.continuous &&
      opts.node?.closest?.('[data-candidate-pdf-report="personality-results"]');
    const personalityQuickPdf = personalityResultsPdf &&
      opts.node?.querySelector?.(".personality-quick-view");
    const personalityDescriptionsPdf = personalityResultsPdf &&
      opts.node?.querySelector?.(".personality-trait-descriptions-view");
    const managerReportPdf = opts.continuous &&
      opts.node?.matches?.('[data-manager-report-pdf-layout="a4-portrait"]');
    const protectedRanges = managerReportPdf
      ? getManagerReportPageGuides(opts.node, source, maxHeight)
      : motivationPdf
      ? getMotivationPageGuides(opts.node, source)
      : (motivationQuestionsPdf || cognitiveQuestionsPdf || personalityQuestionsPdf ||
         combinedInterviewQuestionsPdf)
        ? getMotivationQuestionsPageGuides(opts.node, source)
        : cognitiveResultsPdf
          ? getCognitiveResultsPageGuides(opts.node, source)
          : personalityResultsPdf
            ? personalityDescriptionsPdf
              ? getPersonalityDescriptionPageGuides(opts.node, source, maxHeight)
              : personalityQuickPdf
                ? getPersonalityQuickPageGuides(opts.node, source, maxHeight)
                : getPersonalityResultsPageGuides(opts.node, source, maxHeight)
            : [];
    const slices = calculatePageSlices(
      source.height, maxHeight, breakpoints, protectedRanges
    );

    slices.forEach(slice => {
      if (opts.pageCount.value > 0) pdf.addPage();
      const image = document.createElement("canvas");
      image.width = source.width;
      image.height = slice.height;
      const ctx = image.getContext("2d");
      if (!ctx) throw new Error("Could not render a PDF page.");
      ctx.drawImage(
        source, 0, slice.start, source.width, slice.height,
        0, 0, source.width, slice.height
      );
      pdf.addImage(
        image.toDataURL("image/jpeg", .91), "JPEG",
        margin, margin, width, slice.height / pixelsPerMm,
        undefined, "FAST"
      );
      if (!opts.cover) {
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(8);
        pdf.setTextColor(128);
        pdf.text(String(opts.pageCount.value + 1), pageW - margin, pageH - 4, { align: "right" });
      }
      image.width = 0;
      image.height = 0;
      opts.pageCount.value += 1;
    });
  }

  async function exportSections(sections, options) {
    await ensureLibraries();
    if (!sections || !sections.length) throw new Error("There is no report content.");
    const pdf = new window.jspdf.jsPDF({
      orientation: "portrait", unit: "mm", format: "a4", compress: true
    });
    pdf.setProperties({
      title: options.title || "Talena report",
      subject: options.subject || "Assessment report",
      author: "Talena",
      creator: "Talena",
      keywords: ""
    });
    const pageCount = { value: 0 };
    for (let i = 0; i < sections.length; i += 1) {
      options.onProgress?.(i + 1, sections.length);
      const item = sections[i];
      const canvas = await capture(item.node);
      try {
        addCanvasPages(pdf, canvas, { cover: Boolean(item.cover), continuous: Boolean(item.continuous), node: item.node, pageCount });
      } finally {
        canvas.width = 0;
        canvas.height = 0;
      }
    }
    if (pageCount.value < 1) throw new Error("The report could not be rendered.");
    // A ZIP download needs one in-memory PDF blob per person. Never trigger
    // standalone downloads while building an archive.
    if (options.returnBlob) {
      return new Blob([pdf.output("arraybuffer")], { type: "application/pdf" });
    }
    pdf.save(options.filename || "talena-report.pdf");
  }

  window.TalenaPdfExport = Object.freeze({ ensureLibraries, exportSections, calculatePageSlices });
})();
