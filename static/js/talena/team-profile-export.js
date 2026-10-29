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
    let activeItemStatus = null;

    function updateStatus(text, error) {
      [status, activeItemStatus].filter(Boolean).forEach(function (target) {
        target.textContent = text;
        target.classList.toggle("text-danger", Boolean(error));
        target.classList.toggle("text-muted", !error);
      });
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

    // Both the single-PDF button and ZIP call this same export path. The
    // company branding is already tenant-scoped by the authorized team view.
    function createBrandedCover(profile) {
      const page = document.querySelector(".talena-team-page[data-team-report-brand-primary]");
      if (!page) throw new Error("Company report branding is unavailable");

      const primary = /^#[0-9a-f]{6}$/i.test(page.dataset.teamReportBrandPrimary || "")
        ? page.dataset.teamReportBrandPrimary : "#FF6F61";
      const cover = document.createElement("div");
      cover.className = "talena-team-pdf-cover team-profile-pdf-cover";
      cover.style.setProperty("--team-pdf-primary", primary);
      const focus = Number(page.dataset.teamReportBrandFocus);
      cover.style.backgroundPosition = "center " +
        (Number.isFinite(focus) ? Math.max(0, Math.min(100, focus)) : 50) + "%";

      const background = page.dataset.teamReportBrandCover || "";
      if (background) {
        cover.style.backgroundImage =
          'linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.72)),url("' +
          background.replace(/"/g, "%22") + '")';
      }

      const brand = document.createElement("div");
      brand.className = "talena-team-pdf-cover-brand";
      const logo = page.dataset.teamReportBrandLogo || "";
      if (logo) {
        const image = document.createElement("img");
        image.src = logo;
        image.alt = "";
        brand.appendChild(image);
      } else {
        brand.classList.add("talena-team-pdf-cover-brand-fallback");
        brand.textContent = page.dataset.teamReportCompany || "Talena";
      }

      const footer = document.createElement("div");
      footer.className = "talena-team-pdf-cover-title";
      const stripe = document.createElement("div");
      stripe.className = "talena-team-pdf-cover-line";
      const label = document.createElement("p");
      label.className = "talena-team-pdf-cover-kicker";
      label.textContent = copy.title;
      const name = document.createElement("h1");
      name.textContent = profile.dataset.reportName || copy.title;
      const teamName = document.createElement("p");
      teamName.textContent = page.dataset.teamReportName || "";
      footer.append(stripe, label, name, teamName);
      cover.append(brand, footer);
      return cover;
    }

    // Export the candidate's existing Team styles panel, prefixed with the
    // same branded cover used by the shared report. No server-side PDF files,
    // Sova requests or third-party report processors are involved.
    async function createPdf(profile) {
      const previouslyOpen = profile.open;
      let stage = null;
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

        const page = document.querySelector(".talena-team-page[data-team-report-brand-primary]");
        stage = document.createElement("div");
        stage.className = "talena-team-page team-profile-pdf-stage";
        stage.style.setProperty("--team-report-accent", page.dataset.teamReportBrandPrimary || "#FF6F61");
        stage.style.setProperty("--team-report-accent-light", page.dataset.teamReportBrandLight || "#FFF0ED");
        stage.style.setProperty("--team-report-accent-dark", page.dataset.teamReportBrandDark || "#C94D41");

        const cover = createBrandedCover(profile);
        const body = document.createElement("main");
        body.className = "team-profile-pdf-body";
        const header = document.createElement("header");
        header.className = "team-profile-pdf-heading";
        const h1 = document.createElement("h1");
        h1.textContent = copy.title;
        const candidateName = document.createElement("p");
        candidateName.textContent = profile.dataset.reportName || "";
        header.append(h1, candidateName);
        body.append(header, copyReport);
        stage.append(cover, body);
        document.body.appendChild(stage);
        if (document.fonts?.ready) await document.fonts.ready;
        await nextFrame();

        // The shared engine packs content continuously and returns a single
        // PDF Blob. The ZIP code reuses exactly the same output as "Download".
        return await window.TalenaPdfExport.exportSections(
          [{ node: cover, cover: true }, { node: body, continuous: true }],
          {
            title: copy.title + ": " + (profile.dataset.reportName || ""),
            subject: "Individual team style profile",
            returnBlob: true
          }
        );
      } finally {
        stage?.remove();
        profile.open = previouslyOpen;
      }
    }

    async function runExport(button, action) {
      if (busy) return;
      section.querySelectorAll("[data-team-export-item-status]").forEach(node => {
        node.textContent = "";
      });
      activeItemStatus = button.closest("[data-team-member-profile]")
        ?.querySelector("[data-team-export-item-status]") || null;
      if (isAnonymous()) {
        updateStatus(copy.anonymous, true);
        activeItemStatus = null;
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
        activeItemStatus = null;
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
