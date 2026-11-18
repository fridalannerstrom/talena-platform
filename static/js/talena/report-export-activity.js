/* #435. Browser-only, best-effort report export receipt. No PDF bytes or names. */
(function () {
  "use strict";
  if (window.TalenaReportExportActivity) return;
  const allowed = /^[a-z][a-z0-9-]{1,63}$/;
  const cookie = (name) => {
    const item = document.cookie.split(";").map(x => x.trim())
      .find(x => x.startsWith(name + "="));
    return item ? decodeURIComponent(item.slice(name.length + 1)) : "";
  };
  async function record(url, reportType) {
    if (!url || !allowed.test(reportType) || typeof fetch !== "function") return false;
    const csrf = cookie("csrftoken") ||
      document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    if (!csrf || !window.crypto?.randomUUID) return false;
    try {
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
        body: JSON.stringify({
          report_type: reportType,
          export_id: window.crypto.randomUUID()
        })
      });
      return response.ok;
    } catch (_) {
      // The file already exists. A transient audit error must not break it.
      return false;
    }
  }
  window.TalenaReportExportActivity = Object.freeze({record});
})();
