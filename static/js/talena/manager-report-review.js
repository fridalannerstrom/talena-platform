/* Human review checkpoint before exporting an AI-assisted manager report.
 * Applies to both the in-report PDF action and the shared PDF registry.
 * No approval is persisted or claimed in audit history. Each download
 * requires its own explicit confirmation; cancelling never creates a PDF.
 */
(() => {
  "use strict";
  if (window.TalenaManagerReportReview) return;

  const copy = {
    sv: {
      title: "Har du granskat AI-insikterna?",
      description: "Chefsrapporten innehåller AI-genererade tolkningar. Läs igenom dem och kontrollera att de stämmer med testresultaten, intervjuunderlaget och dina egna bedömningar innan rapporten laddas ner eller delas.",
      noteTitle: "Det är du som ansvarar för innehållet",
      note: "Behöver något korrigeras? Gå tillbaka till chefsrapporten och justera texten innan du laddar ner den.",
      review: "Granska rapporten",
      approve: "Jag har granskat, ladda ner",
    },
    en: {
      title: "Have you reviewed the AI insights?",
      description: "The manager report contains AI-generated interpretations. Review them and check that they align with the assessment results, interview evidence and your own judgement before downloading or sharing the report.",
      noteTitle: "You are responsible for the content",
      note: "Need to correct something? Return to the manager report and edit the text before downloading it.",
      review: "Review report",
      approve: "I've reviewed it, download PDF",
    },
  };

  let nextId = 0;
  const language = () => (
    (document.documentElement.lang || "").toLowerCase().startsWith("sv")
      ? "sv" : "en"
  );

  function returnToReport(report) {
    if (!report?.isConnected) return;
    const heading = report.querySelector(
      ".after-interview-manager-report__title, " +
      ".after-interview-manager-report__header h2, " +
      ".after-interview-manager-report__header h3"
    ) || report;
    heading.scrollIntoView?.({ behavior: "smooth", block: "start" });
    // Give keyboard users a logical focus target when they choose to review.
    const hadTabIndex = heading.hasAttribute("tabindex");
    if (!hadTabIndex) heading.setAttribute("tabindex", "-1");
    heading.focus?.({ preventScroll: true });
    if (!hadTabIndex) {
      heading.addEventListener("blur", () => heading.removeAttribute("tabindex"), { once: true });
    }
  }

  function confirm(report) {
    if (!report?.isConnected ||
        typeof HTMLDialogElement === "undefined" ||
        typeof HTMLDialogElement.prototype.showModal !== "function") {
      return Promise.resolve(false);
    }

    const t = copy[language()];
    const titleId = "talena-manager-ai-review-title-" + (++nextId);
    const descriptionId = "talena-manager-ai-review-description-" + nextId;
    const dialog = document.createElement("dialog");
    dialog.className = "talena-manager-ai-review-dialog";
    dialog.setAttribute("aria-labelledby", titleId);
    dialog.setAttribute("aria-describedby", descriptionId);
    dialog.innerHTML = `
      <div class="talena-manager-ai-review-dialog__content">
        <div class="talena-manager-ai-review-dialog__header">
          <span class="talena-manager-ai-review-dialog__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3 3.5 7.5v9L12 21l8.5-4.5v-9L12 3Z"></path>
              <path d="m9 12 2 2 4-4"></path>
            </svg>
          </span>
          <div class="talena-manager-ai-review-dialog__heading">
            <h3 id="${titleId}">${t.title}</h3>
            <p id="${descriptionId}">${t.description}</p>
          </div>
        </div>
        <div class="talena-manager-ai-review-dialog__notice">
          <strong>${t.noteTitle}</strong>
          <p>${t.note}</p>
        </div>
        <div class="talena-manager-ai-review-dialog__actions">
          <button type="button" class="talena-manager-ai-review-dialog__review"
            data-manager-ai-review-back>${t.review}</button>
          <button type="button" class="talena-manager-ai-review-dialog__approve"
            data-manager-ai-review-confirm>${t.approve}</button>
        </div>
      </div>`;

    // Append inside the live candidate sheet. This keeps native <dialog>
    // focus compatible with its Bootstrap offcanvas focus trap.
    const host = report.closest(".candidate-sheet-layout") ||
      report.closest("[data-candidate-insights-workspace]") || report;
    const previouslyFocused = document.activeElement;
    host.appendChild(dialog);

    return new Promise(resolve => {
      const approve = dialog.querySelector("[data-manager-ai-review-confirm]");
      const review = dialog.querySelector("[data-manager-ai-review-back]");
      const closeWith = (value) => dialog.close(value);
      const onApprove = () => closeWith("approved");
      const onReview = () => closeWith("review");
      const onBackdrop = event => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right ||
            event.clientY < rect.top || event.clientY > rect.bottom) {
          closeWith("review");
        }
      };
      const onClose = () => {
        const accepted = dialog.returnValue === "approved";
        approve.removeEventListener("click", onApprove);
        review.removeEventListener("click", onReview);
        dialog.removeEventListener("click", onBackdrop);
        dialog.remove();
        if (!accepted) returnToReport(report);
        else if (previouslyFocused?.isConnected) {
          previouslyFocused.focus?.({ preventScroll: true });
        }
        resolve(accepted);
      };
      dialog.returnValue = "review"; // Escape and backdrop always cancel.
      approve.addEventListener("click", onApprove);
      review.addEventListener("click", onReview);
      dialog.addEventListener("click", onBackdrop);
      dialog.addEventListener("close", onClose, { once: true });
      try {
        dialog.showModal();
      } catch (error) {
        // Fail closed if the candidate sheet is removed or dialog cannot open.
        console.error("Could not open manager report review dialog:", error);
        if (dialog.isConnected) dialog.remove();
        returnToReport(report);
        resolve(false);
      }
    });
  }

  window.TalenaManagerReportReview = Object.freeze({ confirm });
})();
