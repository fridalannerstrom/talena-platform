(function () {
  "use strict";

  function initTeamProfileExports() {
    const section = document.querySelector("[data-team-profile-section]");
    if (!section) return;

    const profiles = Array.from(section.querySelectorAll("[data-team-member-profile]"));
    const allButton = document.querySelector("[data-team-export-all]");
    const status = document.querySelector("[data-team-export-status]");
    const swedish = (document.documentElement.lang || "").toLowerCase().startsWith("sv");
    const copy = swedish ? {
      exporting: "Skapar PDF",
      packing: "Packar nedladdningen…",
      ready: "Nedladdningen är klar.",
      error: "Teamprofilerna kunde inte laddas ner. Försök igen.",
      anonymous: "Stäng av anonymisering innan du laddar ner identifierande teamprofiler.",
      empty: "Det finns inga färdiga teamprofiler att ladda ner.",
      missing: "personer saknar teamprofil. Vill du ladda ner endast de tillgängliga?",
      title: "Individuell teamprofil",
      all: "Alla teamprofiler"
    } : {
      exporting: "Creating PDF",
      packing: "Preparing download…",
      ready: "Download ready.",
      error: "Team profiles could not be downloaded. Please try again.",
      anonymous: "Turn off anonymisation before downloading identifiable team profiles.",
      empty: "No completed team profiles are available for download.",
      missing: "members have no team profile. Download only the available profiles?",
      title: "Individual team profile",
      all: "All team profiles"
    };

    let librariesPromise = null;
    let busy = false;

    function updateStatus(text, error) {
      if (!status) return;
      status.textContent = text;
      status.classList.toggle("text-danger", Boolean(error));
      status.classList.toggle("text-muted", !error);
    }

    function isAnonymous() {
      return document.getElementById("teamAnonymityToggle")?.getAttribute("aria-checked") === "true";
    }

    function safeName(value) {
      return String(value || "").trim()
        .normalize("NFKC")
        .replace(/[^\p{L}\p{N}._-]+/gu, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 70) || "team-profile";
    }

    function filename(profile) {
      return safeName(profile.dataset.reportName) + "-" +
        safeName(profile.dataset.memberId) + ".pdf";
    }

    function loadLibrary(id, url, isLoaded) {
      if (isLoaded()) return Promise.resolve();
      return new Promise(function (resolve, reject) {
        const script = document.createElement("script");
        script.id = id;
        script.src = url;
        script.crossOrigin = "anonymous";
        script.referrerPolicy = "no-referrer";
        script.onload = function () {
          if (isLoaded()) resolve();
          else reject(new Error("Library failed to initialise"));
        };
        script.onerror = function () {
          script.remove();
          reject(new Error("Library could not be loaded"));
        };
        document.head.appendChild(script);
      });
    }

    function ensureLibraries(includeZip) {
      if (!librariesPromise) {
        librariesPromise = Promise.all([
          loadLibrary(
            "talena-team-html2canvas",
            "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
            () => typeof window.html2canvas === "function"
          ),
          loadLibrary(
            "talena-team-jspdf",
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/4.2.1/jspdf.umd.min.js",
            () => typeof window.jspdf?.jsPDF === "function"
          )
        ]).catch(function (error) {
          librariesPromise = null;
          throw error;
        });
      }
      return librariesPromise.then(function () {
        if (!includeZip) return;
        return loadLibrary(
          "talena-team-jszip",
          "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js",
          () => typeof window.JSZip === "function"
        );
      });
    }

    function nextFrame() {
      return new Promise(resolve => window.requestAnimationFrame(resolve));
    }

    function saveBlob(blob, name) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    }

    // Build PDFs from the same HTML used by the candidate Team styles panel.
    // Never send report data to a PDF API, or persist it in the application's media storage.
    async function createPdf(profile) {
      const previouslyOpen = profile.open;
      let stage = null;
      let sourceCanvas = null;
      try {
        profile.open = true;
        await nextFrame();
        const chart = window.TalenaTeamProfileCharts?.render(profile);
        if (!chart) throw new Error("Team style chart is unavailable");
        chart.resize();
        await nextFrame();
        await nextFrame();

        const report = profile.querySelector("[data-team-report]");
        if (!report) throw new Error("Team profile is unavailable");

        const copyReport = report.cloneNode(true);
        const originalCanvases = report.querySelectorAll("canvas");
        copyReport.querySelectorAll("canvas").forEach(function (canvas, index) {
          const original = originalCanvases[index];
          if (!original || !original.width || !original.height) {
            throw new Error("Team style chart could not be rendered");
          }
          const img = document.createElement("img");
          img.src = original.toDataURL("image/png");
          img.alt = canvas.getAttribute("aria-label") || "";
          img.style.cssText = "display:block;width:100%;height:100%;object-fit:contain;";
          canvas.replaceWith(img);
        });

        copyReport.querySelectorAll("details").forEach(d => { d.open = true; });
        stage = document.createElement("div");
        stage.className = "talena-team-page team-profile-pdf-stage";
        const header = document.createElement("header");
        header.className = "team-profile-pdf-heading";
        const h1 = document.createElement("h1");
        h1.textContent = copy.title;
        const candidateName = document.createElement("p");
        candidateName.textContent = profile.dataset.reportName || "";
        header.append(h1, candidateName);
        stage.append(header, copyReport);
        document.body.appendChild(stage);
        if (document.fonts?.ready) await document.fonts.ready;
        await nextFrame();

        sourceCanvas = await window.html2canvas(stage, {
          backgroundColor: "#ffffff",
          scale: 1.5,
          useCORS: true,
          logging: false,
          scrollX: 0,
          scrollY: 0,
          windowWidth: Math.max(document.documentElement.clientWidth, 1000)
        });
        if (!sourceCanvas.width || !sourceCanvas.height) {
          throw new Error("Empty PDF page");
        }

        const pdf = new window.jspdf.jsPDF({
          orientation: "portrait", unit: "mm", format: "a4", compress: true
        });
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 12;
        const outputWidth = pageWidth - margin * 2;
        const outputHeight = pageHeight - margin * 2;
        const pixelsPerMm = sourceCanvas.width / outputWidth;
        const maxSliceHeight = Math.floor(outputHeight * pixelsPerMm);
        const top = stage.getBoundingClientRect().top;
        const scale = sourceCanvas.width / stage.getBoundingClientRect().width;
        const boundaries = Array.from(stage.querySelectorAll(".team-style-profile-card"))
          .map(node => Math.round((node.getBoundingClientRect().top - top) * scale))
          .filter(position => position > 0 && position < sourceCanvas.height)
          .sort((a, b) => a - b);

        let offset = 0;
        let pageNumber = 0;
        while (offset < sourceCanvas.height) {
          const pageEnd = Math.min(offset + maxSliceHeight, sourceCanvas.height);
          const possible = boundaries.filter(position =>
            position >= offset + maxSliceHeight * 0.6 && position <= pageEnd
          );
          const sliceEnd = pageEnd < sourceCanvas.height && possible.length
            ? possible[possible.length - 1] : pageEnd;
          const sliceHeight = Math.max(1, sliceEnd - offset);
          const pageCanvas = document.createElement("canvas");
          pageCanvas.width = sourceCanvas.width;
          pageCanvas.height = sliceHeight;
          const ctx = pageCanvas.getContext("2d");
          if (!ctx) throw new Error("Could not create PDF page");
          ctx.drawImage(
            sourceCanvas, 0, offset, sourceCanvas.width, sliceHeight,
            0, 0, pageCanvas.width, pageCanvas.height
          );
          if (pageNumber > 0) pdf.addPage();
          pdf.addImage(
            pageCanvas.toDataURL("image/jpeg", 0.89),
            "JPEG", margin, margin, outputWidth, sliceHeight / pixelsPerMm,
            undefined, "FAST"
          );
          pageCanvas.width = 0;
          pageCanvas.height = 0;
          offset = sliceEnd;
          pageNumber += 1;
        }
        return new Blob([pdf.output("arraybuffer")], { type: "application/pdf" });
      } finally {
        if (sourceCanvas) {
          sourceCanvas.width = 0;
          sourceCanvas.height = 0;
        }
        stage?.remove();
        profile.open = previouslyOpen;
      }
    }

    async function runExport(button, action) {
      if (busy) return;
      if (isAnonymous()) {
        updateStatus(copy.anonymous, true);
        return;
      }
      busy = true;
      const buttons = document.querySelectorAll("[data-team-export-all], [data-team-export-single]");
      buttons.forEach(b => { b.disabled = true; });
      button.setAttribute("aria-busy", "true");
      updateStatus("");
      try {
        await action();
        updateStatus(copy.ready);
      } catch (error) {
        console.error("Team profile PDF export failed:", error);
        updateStatus(copy.error, true);
      } finally {
        buttons.forEach(b => { b.disabled = false; });
        button.removeAttribute("aria-busy");
        busy = false;
      }
    }

    section.querySelectorAll("[data-team-export-single]").forEach(function (button) {
      button.addEventListener("click", function () {
        const profile = button.closest("[data-team-member-profile]");
        if (!profile) return;
        runExport(button, async function () {
          await ensureLibraries(false);
          updateStatus(copy.exporting + "…");
          saveBlob(await createPdf(profile), filename(profile));
        });
      });
    });

    allButton?.addEventListener("click", function () {
      const available = profiles.filter(profile => profile.dataset.hasReport === "true");
      const missing = profiles.length - available.length;
      if (!available.length) {
        updateStatus(copy.empty, true);
        return;
      }
      if (isAnonymous()) {
        updateStatus(copy.anonymous, true);
        return;
      }
      if (missing > 0 && !window.confirm(missing + " " + copy.missing)) return;

      runExport(allButton, async function () {
        await ensureLibraries(true);
        const zip = new window.JSZip();
        for (let i = 0; i < available.length; i += 1) {
          updateStatus(copy.exporting + " " + (i + 1) + "/" + available.length + "…");
          const blob = await createPdf(available[i]);
          zip.file(filename(available[i]), blob);
        }
        updateStatus(copy.packing);
        const archive = await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
        const team = safeName(section.dataset.teamName);
        saveBlob(archive, team + "-teamprofiler.zip");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTeamProfileExports, { once: true });
  } else {
    initTeamProfileExports();
  }
})();
