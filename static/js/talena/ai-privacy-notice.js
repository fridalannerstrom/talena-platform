(() => {
  "use strict";

  // Display an informational notice only after the backend confirms an
  // outbound OpenAI request contained text that it actually masked.
  // Never receive or display the original identifier.
  const EVENT_TYPE = "ai_privacy_masked";
  const HEADER = "X-Talena-AI-PII-Masked";
  const originalFetch = window.fetch;
  if (typeof originalFetch !== "function") return;

  let notice;
  let dismissalTimer;

  function content() {
    const swedish = (document.documentElement.lang || "en")
      .toLowerCase().startsWith("sv");
    return swedish
      ? {
          title: "Personuppgifter har maskats",
          body: "Identifierande uppgifter har maskats i underlaget till AI. Dina sparade anteckningar har inte ändrats.",
          close: "Stäng meddelande",
        }
      : {
          title: "Personal data has been masked",
          body: "Identifying details were masked in the information sent to AI. Your saved notes have not been changed.",
          close: "Dismiss notification",
        };
  }

  function showNotice() {
    if (!document.body) return;
    if (!notice) {
      const copy = content();
      notice = document.createElement("div");
      notice.className = "talena-ai-privacy-toast";
      notice.setAttribute("role", "status");
      notice.setAttribute("aria-live", "polite");
      notice.dataset.aiPrivacyToast = "";
      const text = document.createElement("div");
      text.className = "talena-ai-privacy-toast__content";
      const title = document.createElement("strong");
      title.textContent = copy.title;
      const description = document.createElement("p");
      description.textContent = copy.body;
      text.append(title, description);
      const close = document.createElement("button");
      close.type = "button";
      close.className = "talena-ai-privacy-toast__close";
      close.setAttribute("aria-label", copy.close);
      close.textContent = "×";
      close.addEventListener("click", () => {
        notice.hidden = true;
        window.clearTimeout(dismissalTimer);
      });
      notice.append(text, close);
      document.body.append(notice);
    }
    notice.hidden = false;
    window.clearTimeout(dismissalTimer);
    dismissalTimer = window.setTimeout(() => {
      notice.hidden = true;
    }, 12000);
  }

  function scanLine(line) {
    // A privacy event is a small, fixed JSON object. Don't inspect or log
    // arbitrary candidate data from other NDJSON stream events.
    if (line.length > 140 || !line.includes(EVENT_TYPE)) return;
    try {
      if (JSON.parse(line).type === EVENT_TYPE) showNotice();
    } catch (_) {
      // Ignore incomplete or irrelevant stream events.
    }
  }

  function monitorStream(stream) {
    if (typeof TransformStream !== "function") return stream;
    const decoder = new TextDecoder("utf-8");
    let pending = "";
    return stream.pipeThrough(new TransformStream({
      transform(chunk, controller) {
        pending += decoder.decode(chunk, { stream: true });
        const lines = pending.split("\n");
        pending = lines.pop() || "";
        lines.forEach(scanLine);
        // Bound incidental buffering. Only short privacy events are relevant.
        if (pending.length > 4096) pending = pending.slice(-140);
        controller.enqueue(chunk); // Preserve the original response bytes.
      },
      flush() {
        pending += decoder.decode();
        if (pending.trim()) scanLine(pending.trim());
      },
    }));
  }

  window.fetch = async function talenaPrivacyAwareFetch(...args) {
    const response = await originalFetch.apply(this, args);
    if (!response.ok) return response;
    if (response.headers.get(HEADER) === "1") showNotice();

    if (
      !response.body ||
      !(response.headers.get("content-type") || "").toLowerCase()
        .includes("application/x-ndjson") ||
      typeof Response !== "function" ||
      typeof TransformStream !== "function"
    ) return response;

    // Preserve response status, headers and untouched NDJSON bytes. The
    // lightweight stream observer only reacts to an explicit backend event.
    const result = new Response(monitorStream(response.body), {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
    for (const prop of ["url", "redirected", "type"]) {
      try {
        Object.defineProperty(result, prop, { value: response[prop] });
      } catch (_) {
        // These attributes are informational, not needed for stream parsing.
      }
    }
    return result;
  };
})();
