/* #180: export the shared team overview, distinct from individual #181 reports.
   Export is created in the authorized browser. Anonymous mode is fail-closed and
   includes only predefined aggregate cards, never member/AI/context sections. */
(function () {
  "use strict";

  function init() {
    const page = document.querySelector(".talena-team-page[data-team-report-brand-primary]");
    const button = page?.querySelector("[data-team-report-download]");
    const status = page?.querySelector("[data-team-report-download-status]");
    if (!page || !button || !status) return;

    const swedish = (document.documentElement.lang || "").toLowerCase().startsWith("sv");
    const copy = swedish ? {
      creating: "Skapar teamrapport",
      ready: "Teamrapporten har laddats ner.",
      failed: "Teamrapporten kunde inte skapas. Försök igen.",
      noData: "Det finns ingen färdig teamdata att exportera.",
      privacy: "Den anonyma rapporten kunde inte verifieras. Inget laddades ner.",
      named: "Teamrapport",
      anonymous: "Anonymiserad teamrapport",
      anonymousNotice: "Enbart aggregerade teamresultat ingår i anonymiserat läge."
    } : {
      creating: "Creating team report",
      ready: "Team report downloaded.",
      failed: "The team report could not be created. Please try again.",
      noData: "No completed team data is available for export.",
      privacy: "Anonymous report privacy verification failed. No file was downloaded.",
      named: "Team report",
      anonymous: "Anonymised team report",
      anonymousNotice: "Anonymous export contains aggregate results only."
    };

    function anonymousMode() {
      return page.querySelector("#teamAnonymityToggle")?.getAttribute("aria-checked") === "true";
    }
    function newElement(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }
    function sanitizeStage(node, anonymous) {
      // Identity-bearing extremum attribution is part of the visible named
      // report only. Anonymous export must never clone it, including hidden
      // panels, initials, tooltips and original-text attributes.
      if (anonymous) node.querySelectorAll("[data-team-chart-person-details]").forEach(x => x.remove());
      node.querySelectorAll("button, form, a, input, textarea, select, .team-insight-actions, .team-member-profile-toolbar, [data-team-insight-status]").forEach(x => x.remove());
      const sourceCanvases = node.querySelectorAll("canvas");
      sourceCanvases.forEach(canvas => {
        const original = document.getElementById(canvas.id);
        if (!original || !original.width || !original.height) {
          throw new Error("The team chart is unavailable.");
        }
        const image = document.createElement("img");
        image.src = original.toDataURL("image/png");
        image.style.cssText = "display:block;width:100%;height:100%;object-fit:contain";
        canvas.replaceWith(image);
      });
      node.querySelectorAll("*").forEach(element => {
        Array.from(element.attributes).forEach(attr => {
          if (attr.name.startsWith("data-") || attr.name === "title" || attr.name.startsWith("aria-")) {
            element.removeAttribute(attr.name);
          }
        });
      });
    }

    function makeCover(anonymous) {
      const primary = /^#[\da-f]{6}$/i.test(page.dataset.teamReportBrandPrimary || "")
        ? page.dataset.teamReportBrandPrimary : "#FF6F61";
      const cover = newElement("div", "talena-team-pdf-cover");
      cover.style.setProperty("--team-pdf-primary", primary);
      const focusValue = Number(page.dataset.teamReportBrandFocus);
      const focusY = Number.isFinite(focusValue) ? Math.max(0, Math.min(100, focusValue)) : 50;
      cover.style.backgroundPosition = "center " + focusY + "%";
      const photo = page.dataset.teamReportBrandCover || "";
      if (photo) cover.style.backgroundImage = 'linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.72)),url("' + photo.replace(/"/g, "%22") + '")';

      const brandHeader = newElement("div", "talena-team-pdf-cover-brand");
      const logo = page.dataset.teamReportBrandLogo;
      if (logo) {
        const image = newElement("img");
        image.src = logo;
        image.alt = "";
        brandHeader.append(image);
      } else {
        brandHeader.classList.add("talena-team-pdf-cover-brand-fallback");
        brandHeader.textContent = anonymous ? "Talena" : (page.dataset.teamReportCompany || "Talena");
      }
      const bottom = newElement("div", "talena-team-pdf-cover-title");
      bottom.append(
        newElement("div", "talena-team-pdf-cover-line"),
        newElement("p", "talena-team-pdf-cover-kicker", anonymous ? copy.anonymous : copy.named),
        newElement("h1", "", anonymous ? copy.anonymous : (page.dataset.teamReportName || copy.named))
      );
      if (anonymous) bottom.append(newElement("p", "", copy.anonymousNotice));
      else bottom.append(newElement("p", "", page.dataset.teamReportCompany || "Talena"));
      cover.append(brandHeader, bottom);
      return cover;
    }

    function sourceSelectors(anonymous) {
      // Deliberately limited allowlist: member identifiers, narrative AI and
      // arbitrary context are excluded ENTIRELY in anonymised exports.
      if (anonymous) return [
        "[data-team-report-summary]",
        "[data-team-report-composite]",
        "[data-team-report-maximum-numeric]"
      ];
      return [
        "[data-team-report-context]",
        "[data-team-report-summary]",
        "[data-team-report-composite]",
        "[data-team-report-insights]",
        "[data-team-report-maximum]",
        "[data-team-report-members]"
      ];
    }

    function assertAnonymousSafe(node) {
      const visible = (node.textContent || "").toLocaleLowerCase();
      const identities = Array.from(page.querySelectorAll("[data-team-member-profile]"))
        .flatMap(profile => [
          profile.dataset.reportName,
          profile.querySelector(".team-member-profile-email")?.dataset.originalText
            || profile.querySelector(".team-member-profile-email")?.textContent
        ])
        .filter(x => typeof x === "string" && x.trim().length > 2);
      if (identities.some(identity => visible.includes(identity.trim().toLocaleLowerCase()))) {
        throw new Error(copy.privacy);
      }
      // All candidate/member elements must stay outside the anonymous stage.
      if (node.querySelector("[data-team-member-profile], .team-score-badge, .team-member-profile-name, .team-member-profile-email, .team-table, [data-team-report-members]")) {
        throw new Error(copy.privacy);
      }
    }

    // #449: render the same authorised report to an in-memory PDF for either
    // the original single-file button or the new report-package picker.
    const currentPage = () => page.isConnected &&
      document.querySelector(".talena-team-page[data-team-report-brand-primary]") === page;
    const hasResults = () => currentPage() &&
      !!page.querySelector("[data-team-report-summary]") &&
      !!page.querySelector("[data-team-report-composite]");
    let packageBusy = false;
    let rendering = false;

    async function renderPdf(options = {}) {
      if (!hasResults()) throw new Error(copy.noData);
      if (rendering) throw new Error(copy.failed);
      rendering = true;
      const anonymous = anonymousMode();
      let stage;
      try {
        const sources = sourceSelectors(anonymous)
          .map(selector => page.querySelector(selector)).filter(Boolean);
        // Do not clone the page itself. It contains member names, e-mails
        // and hidden identifying data outside the explicit source allowlist.
        stage = newElement("div", "talena-team-page team-report-pdf-stage");
        stage.style.setProperty("--team-report-accent", page.dataset.teamReportBrandPrimary || "#FF6F61");
        stage.style.setProperty("--team-report-accent-light", page.dataset.teamReportBrandLight || "#FFF0ED");
        stage.style.setProperty("--team-report-accent-dark", page.dataset.teamReportBrandDark || "#C94D41");
        const cover = makeCover(anonymous);
        const parts = sources.map(source => {
          const node = newElement("section", "team-report-pdf-part");
          node.append(source.cloneNode(true));
          sanitizeStage(node, anonymous);
          return node;
        });
        const body = newElement("main", "team-report-pdf-body");
        body.append(...parts);
        stage.append(cover, body);
        document.body.appendChild(stage);
        if (anonymous) assertAnonymousSafe(stage);
        const title = anonymous ? copy.anonymous : copy.named;
        const filename = anonymous ? "anonym-teamrapport.pdf" : "teamrapport.pdf";
        if (!currentPage() || anonymousMode() !== anonymous) throw Error(copy.privacy);
        const pdf = await window.TalenaPdfExport.exportSections(
          [{node:cover,cover:true},{node:body,continuous:true}],
          {
            title, subject: anonymous ? "Aggregated team scores" : "Team assessment report",
            filename, returnBlob: Boolean(options.returnBlob), onProgress: options.onProgress
          }
        );
        // If the viewer changed to anonymised mode while rendering, discard
        // any personally identifiable PDF blob instead of offering a download.
        if (!currentPage() || anonymousMode() !== anonymous) throw Error(copy.privacy);
        return pdf;
      } finally {
        stage?.remove();
        rendering = false;
      }
    }
    function beginPackage() {
      // The composite report is optional in a package. Complete individual
      // profiles can still be selected when the composite is unavailable.
      if (!currentPage() || anonymousMode() ||
          button.disabled || rendering || packageBusy) return false;
      packageBusy = true;
      button.disabled = true;
      return true;
    }
    function endPackage() {
      packageBusy = false;
      button.disabled = false;
    }
    async function exportReportForPackage() {
      if (!packageBusy || anonymousMode() || !hasResults()) throw Error(copy.privacy);
      const blob = await renderPdf({returnBlob:true});
      if (!packageBusy || !currentPage() || anonymousMode()) throw Error(copy.privacy);
      return blob;
    }
    async function exportCoverForPackage(packageTitle) {
      if (!packageBusy || anonymousMode() || !currentPage()) throw Error(copy.privacy);
      const stage = newElement("div", "talena-team-page team-report-pdf-stage");
      stage.style.setProperty("--team-report-accent", page.dataset.teamReportBrandPrimary || "#FF6F61");
      stage.style.setProperty("--team-report-accent-light", page.dataset.teamReportBrandLight || "#FFF0ED");
      stage.style.setProperty("--team-report-accent-dark", page.dataset.teamReportBrandDark || "#C94D41");
      const cover = makeCover(false);
      const heading = cover.querySelector("h1");
      if (heading) heading.textContent = String(packageTitle || copy.named).slice(0,90);
      stage.append(cover);
      document.body.append(stage);
      try {
        if (!currentPage() || anonymousMode()) throw Error(copy.privacy);
        const blob = await window.TalenaPdfExport.exportSections(
          [{node:cover,cover:true}],
          {title:String(packageTitle || copy.named),subject:"Team report package",returnBlob:true}
        );
        if (!currentPage() || anonymousMode()) throw Error(copy.privacy);
        return blob;
      } finally {
        stage.remove();
      }
    }
    window.TalenaTeamReportExport = Object.freeze({
      isCurrent:currentPage, isAnonymous:anonymousMode,
      getAvailable:() => hasResults() && !anonymousMode(),
      beginPackage,endPackage,exportReportForPackage,exportCoverForPackage
    });

    button.addEventListener("click", async function () {
      if (button.disabled || packageBusy) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      status.classList.remove("text-danger");
      status.textContent = copy.creating + "…";
      try {
        await renderPdf({
          onProgress:(done,total) => {
            status.textContent = copy.creating + " " + done + "/" + total + "…";
          }
        });
        status.textContent = copy.ready;
      } catch (err) {
        // No raw report text or identifying information in browser logs.
        const message = err?.message;
        status.textContent = [copy.noData,copy.privacy].includes(message)
          ? message : copy.failed;
        status.classList.add("text-danger");
      } finally {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
