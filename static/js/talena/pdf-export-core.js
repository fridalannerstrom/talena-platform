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

  function addCanvasPages(pdf, source, opts) {
    if (!source.width || !source.height) throw new Error("PDF page is empty.");
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = opts.cover ? 0 : 12;
    const width = pageW - margin * 2;
    const height = pageH - margin * 2;
    const pixelsPerMm = source.width / width;
    const maxHeight = Math.max(1, Math.floor(height * pixelsPerMm));
    let offset = 0;
    while (offset < source.height) {
      const sliceH = Math.min(maxHeight, source.height - offset);
      if (opts.pageCount.value > 0) pdf.addPage();
      const image = document.createElement("canvas");
      image.width = source.width;
      image.height = sliceH;
      const ctx = image.getContext("2d");
      if (!ctx) throw new Error("Could not render a PDF page.");
      ctx.drawImage(
        source, 0, offset, source.width, sliceH,
        0, 0, source.width, sliceH
      );
      pdf.addImage(
        image.toDataURL("image/jpeg", .91), "JPEG",
        margin, margin, width, sliceH / pixelsPerMm,
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
      offset += sliceH;
      opts.pageCount.value += 1;
    }
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
        addCanvasPages(pdf, canvas, { cover: Boolean(item.cover), pageCount });
      } finally {
        canvas.width = 0;
        canvas.height = 0;
      }
    }
    if (pageCount.value < 1) throw new Error("The report could not be rendered.");
    pdf.save(options.filename || "talena-report.pdf");
  }

  window.TalenaPdfExport = Object.freeze({ ensureLibraries, exportSections });
})();
