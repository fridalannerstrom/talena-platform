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
    function sanitizeStage(node) {
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

    button.addEventListener("click", async function () {
      if (button.disabled) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      status.classList.remove("text-danger");
      status.textContent = copy.creating + "…";

      const anonymous = anonymousMode();
      let stage;
      try {
        const sources = sourceSelectors(anonymous)
          .map(selector => page.querySelector(selector))
          .filter(Boolean);
        if (!page.querySelector("[data-team-report-summary]") || !page.querySelector("[data-team-report-composite]")) {
          throw new Error(copy.noData);
        }

        // Never clone the entire team page: it contains candidates' names,
        // emails, private data attributes and individual report panels.
        stage = newElement("div", "talena-team-page team-report-pdf-stage");
        stage.style.setProperty("--team-report-accent", page.dataset.teamReportBrandPrimary || "#FF6F61");
        stage.style.setProperty("--team-report-accent-light", page.dataset.teamReportBrandLight || "#FFF0ED");
        stage.style.setProperty("--team-report-accent-dark", page.dataset.teamReportBrandDark || "#C94D41");
        const cover = makeCover(anonymous);
        const parts = sources.map(source => {
          const node = newElement("section", "team-report-pdf-part");
          node.append(source.cloneNode(true));
          sanitizeStage(node);
          return node;
        });
        stage.append(cover, ...parts);
        document.body.appendChild(stage);
        if (anonymous) assertAnonymousSafe(stage);
        const title = anonymous ? copy.anonymous : copy.named;
        const filename = anonymous ? "anonym-teamrapport.pdf" : "teamrapport.pdf";
        await window.TalenaPdfExport.exportSections(
          [{ node: cover, cover: true }, ...parts.map(node => ({ node }))],
          {
            title,
            subject: anonymous ? "Aggregated team scores" : "Team assessment report",
            filename,
            onProgress: (done, total) => {
              status.textContent = copy.creating + " " + done + "/" + total + "…";
            }
          }
        );
        status.textContent = copy.ready;
      } catch (err) {
        // Do not log report content or candidate-identifying details.
        const message = err?.message;
        status.textContent = (message === copy.noData || message === copy.privacy)
          ? message : copy.failed;
        status.classList.add("text-danger");
      } finally {
        stage?.remove();
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
