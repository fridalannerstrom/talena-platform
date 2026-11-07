/* #429: Shared, server-attributed Chefsrapport PDF metadata.
 * Never print a client-invented actor or local-download claim.
 */
(() => {
  "use strict";
  if (window.TalenaManagerReportPdf) return;

  const getRoot = (context) =>
    context?.closest?.("[data-final-output-root]") ||
    context?.querySelector?.("[data-final-output-root]");

  const csrfToken = () => {
    const cookie = document.cookie.split("; ").find(part => part.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
  };

  async function prepare(context) {
    const root = getRoot(context);
    const url = root?.dataset?.managerReportPdfPrepareUrl;
    if (!url) throw new Error("Manager report attribution endpoint unavailable");
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    const metadata = await response.json();
    if (!response.ok || metadata?.ok !== true || !metadata.exported_by?.at) {
      throw new Error("Manager report attribution failed");
    }
    return metadata;
  }

  function formattedDate(value, language) {
    const date = new Date(value);
    if (!value || !Number.isFinite(date.getTime())) return "";
    return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-GB", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
      timeZone: "Europe/Stockholm",
    }).format(date);
  }

  function decorate(reportClone, metadata) {
    if (!reportClone || metadata?.ok !== true || !metadata.exported_by) {
      throw new Error("Missing verified PDF attribution");
    }
    // Keep original headings, body text and manual overrides. Strip only UI
    // labels, edit controls, and the associated help tooltip.
    reportClone.querySelectorAll(
      ".talena-ai-generated-badge, .talena-ai-personality-help, " +
      ".after-interview-manager-report__edit-controls, " +
      ".after-interview-manager-report__edited-badge"
    ).forEach(node => node.remove());

    const language = metadata.language === "sv" ? "sv" : "en";
    const labels = language === "sv"
      ? {edited: "Senast redigerad av", exported: "PDF exporterad av"}
      : {edited: "Last edited by", exported: "PDF exported by"};
    const pieces = [];
    if (metadata.last_edited_by?.name && metadata.last_edited_by?.at) {
      pieces.push(labels.edited + " " + metadata.last_edited_by.name +
        " · " + formattedDate(metadata.last_edited_by.at, language));
    }
    pieces.push(labels.exported + " " + metadata.exported_by.name +
      " · " + formattedDate(metadata.exported_by.at, language));

    const note = document.createElement("p");
    note.className = "after-interview-manager-report__pdf-attribution";
    note.textContent = pieces.join("  |  ");
    note.style.cssText =
      "margin:.45rem 0 1rem;padding:.4rem 0 .55rem;border-bottom:1px solid #e8e2de;" +
      "color:#746d67;font-size:10px;font-weight:400;line-height:1.5;" +
      "overflow-wrap:anywhere;break-inside:avoid;";
    const intro = reportClone.querySelector(".after-interview-manager-report__intro");
    if (intro) intro.after(note);
    else reportClone.prepend(note);
    return note;
  }

  window.TalenaManagerReportPdf = Object.freeze({prepare, decorate});
})();
