(() => {
  "use strict";

  const initialisedButtons = new WeakSet();

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const copy = () =>
    isSwedish()
      ? {
          generate: "Generera beslutsstöd efter intervjun",
          regenerate: "Generera uppdaterat beslutsstöd efter intervjun",
          generating: "Sammanställer intervjuunderlaget…",
          error: "Beslutsstödet efter intervjun kunde inte genereras.",
        }
      : {
          generate: "Generate post-interview decision support",
          regenerate: "Generate updated post-interview decision support",
          generating: "Synthesising the interview evidence…",
          error: "The post-interview decision support could not be generated.",
        };

  const getCookie = (name) => {
    const cookie = document.cookie
      .split("; ")
      .find((item) => item.trim().startsWith(`${name}=`));

    return cookie
      ? decodeURIComponent(cookie.trim().slice(name.length + 1))
      : "";
  };

  const hasQuestionEvidence = (root) =>
    Boolean(
      root.querySelector(
        "[data-interview-question-notes-summary-list] .interview-question-notes-summary__item",
      ),
    );

  const parseStreamLine = (line) => {
    const value = String(line || "").trim();
    if (!value) return null;

    try {
      return JSON.parse(value);
    } catch (_error) {
      return null;
    }
  };

  const logPromptDebug = (event) => {
    if (event?.type === "prompt_debug") {
      console.info(
        "[Talena] After interview prompt diagnostics:",
        event.data,
      );
      return;
    }

    if (event?.type === "result_debug") {
      console.info(
        "[Talena] After interview generated-content diagnostics:",
        event.data,
      );
      return;
    }

    if (event?.type === "content_blocks") {
      console.info(
        "[Talena] After interview AI content-block event:",
        Object.fromEntries(
          Object.entries(event.blocks || {}).map(
            ([key, value]) => [key, String(value || "").trim().length],
          ),
        ),
      );
      return;
    }

    if (event?.type === "saved_result") {
      console.info(
        "[Talena] After interview saved-result event:",
        Object.fromEntries(
          Object.entries(event.data?.content_blocks || {}).map(
            ([key, value]) => [key, String(value || "").trim().length],
          ),
        ),
      );
    }
  };

  const consumeStream = async (url) => {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/x-ndjson",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    });

    if (!response.ok) {
      let message = copy().error;

      try {
        const payload = await response.json();
        message = payload.error || payload.message || message;
      } catch (_error) {
        // Keep the translated fallback.
      }

      throw new Error(message);
    }

    if (!response.body) {
      const body = await response.text();
      for (const line of body.split(/\r?\n/)) {
        const event = parseStreamLine(line);
        logPromptDebug(event);
        if (event?.type === "error") {
          throw new Error(event.message || copy().error);
        }
      }
      return;
    }

    console.info("[Talena] After interview stream started:", url);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const result = await reader.read();
      if (result.done) break;

      buffer += decoder.decode(result.value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const event = parseStreamLine(line);
        logPromptDebug(event);
        if (event?.type === "error") {
          throw new Error(event.message || copy().error);
        }
      }
    }

    buffer += decoder.decode();
    const finalEvent = parseStreamLine(buffer);
    logPromptDebug(finalEvent);
    if (finalEvent?.type === "error") {
      throw new Error(finalEvent.message || copy().error);
    }
  };

  const refreshFinalOutput = async (root) => {
    const scope =
      root.closest("[data-candidate-insights-workspace]") ||
      root.parentElement ||
      document;

    if (typeof window.refreshCandidateFinalOutput === "function") {
      await window.refreshCandidateFinalOutput(scope);
    }

    if (typeof window.initCandidateDecisionSupport === "function") {
      window.initCandidateDecisionSupport(scope);
    }

    window.setTimeout(() => ensure(scope), 0);
  };

  const generate = async (root, button, regenerate) => {
    if (button.dataset.questionEvidenceGenerating === "true") return;

    const labels = copy();
    const streamUrl = root.dataset.postInterviewStreamUrl || "";
    const regenerateUrl = root.dataset.postInterviewRegenerateUrl || "";
    const thinking = root.querySelector("[data-post-interview-thinking]");
    const empty = root.querySelector("[data-post-interview-empty]");
    const error = root.querySelector("[data-post-interview-error]");

    button.dataset.questionEvidenceGenerating = "true";
    button.disabled = true;

    if (!button.classList.contains("btn-icon")) {
      button.dataset.originalText = button.textContent || "";
      button.textContent = labels.generating;
    }

    thinking?.classList.remove("d-none");
    error?.classList.add("d-none");

    if (!regenerate) {
      empty?.classList.add("d-none");
    }

    try {
      let effectiveStreamUrl = streamUrl;

      if (regenerate) {
        const response = await fetch(regenerateUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
            Accept: "application/json",
          },
          credentials: "same-origin",
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || labels.error);
        }

        effectiveStreamUrl = payload.stream_url || streamUrl;
      }

      if (!effectiveStreamUrl) {
        throw new Error(labels.error);
      }

      await consumeStream(effectiveStreamUrl);
      await refreshFinalOutput(root);
    } catch (exception) {
      console.error("Question-evidence post-interview generation failed:", exception);

      thinking?.classList.add("d-none");
      error?.classList.remove("d-none");
      if (error) error.textContent = exception.message || labels.error;

      if (!regenerate) {
        empty?.classList.remove("d-none");
      }
    } finally {
      button.dataset.questionEvidenceGenerating = "false";
      button.disabled = false;

      if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
      }

      if (window.feather) window.feather.replace();
    }
  };

  const createGenerateButton = (root) => {
    const empty = root.querySelector("[data-post-interview-empty]");
    if (!empty) return null;

    const labels = copy();
    const wrapper = document.createElement("div");
    wrapper.className = "d-flex justify-content-center mt-4";
    wrapper.dataset.questionEvidencePostAction = "";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-primary";
    button.dataset.questionEvidencePostGenerate = "";
    button.textContent = labels.generate;

    wrapper.appendChild(button);
    empty.appendChild(wrapper);
    return button;
  };

  const createRegenerateButton = (root) => {
    const badge = root.querySelector("[data-post-interview-status-badge]");
    const actions = badge?.parentElement;
    if (!actions) return null;

    const labels = copy();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-icon btn-light";
    button.dataset.questionEvidencePostGenerate = "";
    button.dataset.regenerate = "true";
    button.title = labels.regenerate;
    button.setAttribute("aria-label", labels.regenerate);
    button.innerHTML = '<i data-feather="refresh-cw"></i>';

    actions.appendChild(button);
    return button;
  };

  const initialiseButton = (root, button) => {
    if (!button || initialisedButtons.has(button)) return;

    initialisedButtons.add(button);
    button.addEventListener("click", () => {
      const regenerate = button.dataset.regenerate === "true";
      generate(root, button, regenerate);
    });
  };

  const ensureRoot = (root) => {
    if (!(root instanceof Element)) return;

    const hasEvidence = hasQuestionEvidence(root);
    const dynamicActions = root.querySelectorAll(
      "[data-question-evidence-post-action], [data-question-evidence-post-generate]",
    );

    if (!hasEvidence) {
      dynamicActions.forEach((node) => node.remove());
      return;
    }

    // Server-rendered controls already cover candidates with saved general
    // interview notes. Only add a control when structured question evidence is
    // the reason post-interview synthesis should be available.
    if (root.querySelector("[data-post-interview-generate]")) return;

    const hasResult = root.dataset.hasPostInterviewResult === "true";
    const button = hasResult
      ? createRegenerateButton(root)
      : createGenerateButton(root);

    initialiseButton(root, button);

    if (window.feather) window.feather.replace();
  };

  const ensure = (scope = document) => {
    if (scope instanceof Element && scope.matches("[data-final-output-root]")) {
      ensureRoot(scope);
    }

    scope.querySelectorAll?.("[data-final-output-root]").forEach(ensureRoot);
  };

  document.addEventListener("DOMContentLoaded", () => ensure(document));
  document.addEventListener("candidate-interview-question-note-updated", () => {
    window.setTimeout(() => ensure(document), 0);
  });

  const observer = new MutationObserver(() => ensure(document));
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
