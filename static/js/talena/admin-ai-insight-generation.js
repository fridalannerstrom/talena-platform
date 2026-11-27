/* Admin-only on-demand generation for candidate interpretation insights. */
(function () {
  "use strict";

  const definitions = [
    {
      button: "[data-personality-ai-regenerate]",
      root: "[data-personality-ai-root]",
      label: { sv: "personlighetstolkningen", en: "personality interpretation" },
    },
    {
      button: "[data-motivation-ai-regenerate]",
      root: "[data-motivation-ai-root]",
      label: { sv: "motivationstolkningen", en: "motivation interpretation" },
    },
    {
      button: "[data-cognitive-interpretation-regenerate]",
      root: "[data-cognitive-interpretation-root]",
      label: { sv: "färdighetstolkningen", en: "skills interpretation" },
    },
  ];

  const isSwedish = () => (
    (document.documentElement.lang || "sv").toLowerCase().startsWith("sv")
  );

  function getCookie(name) {
    const prefix = name + "=";
    const item = document.cookie
      .split(";")
      .map(value => value.trim())
      .find(value => value.startsWith(prefix));
    return item ? decodeURIComponent(item.slice(prefix.length)) : "";
  }

  function showStatus(mirror, message, isError = false) {
    if (!mirror) return;
    let status = mirror.querySelector("[data-admin-ai-generation-status]");
    if (!status) {
      status = document.createElement("div");
      status.className = "alert py-2 mb-3";
      status.setAttribute("role", "status");
      status.dataset.adminAiGenerationStatus = "";
      const workspace = mirror.querySelector("[data-candidate-insights-workspace]");
      mirror.insertBefore(status, workspace || mirror.firstChild);
    }
    status.classList.toggle("alert-danger", isError);
    status.classList.toggle("alert-info", !isError);
    status.textContent = message;
    status.hidden = !message;
  }

  async function startAndWait(root) {
    const csrfToken = getCookie("csrftoken");
    const resetResponse = await fetch(root.dataset.regenerateUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    });
    const resetText = await resetResponse.text();
    let resetData = {};
    try { resetData = JSON.parse(resetText); } catch (_) {}
    if (!resetResponse.ok) {
      throw new Error(resetData.error || resetText || "Could not start AI generation.");
    }
    const streamUrl = resetData.stream_url || root.dataset.streamUrl;
    if (!streamUrl) throw new Error("No AI stream URL was returned.");

    const streamResponse = await fetch(streamUrl, {
      headers: {
        "Accept": "application/x-ndjson",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    });
    const body = await streamResponse.text();
    if (!streamResponse.ok) {
      let message = body || "AI generation failed.";
      try { message = JSON.parse(body).error || message; } catch (_) {}
      throw new Error(message);
    }

    let completed = false;
    for (const line of body.split(/\r?\n/).filter(Boolean)) {
      let item;
      try { item = JSON.parse(line); } catch (_) { continue; }
      if (item.type === "error") {
        throw new Error(item.message || "AI generation failed.");
      }
      if (["saved_result", "done", "completed"].includes(item.type)) {
        completed = true;
      }
    }
    if (!completed) throw new Error("AI generation did not finish.");
  }

  async function refreshCandidate(mirror) {
    const sheetBody = document.getElementById("candidateSheetBody");
    const url = sheetBody?.dataset.currentCandidateUrl;
    if (!sheetBody || !url || !mirror.isConnected) {
      window.location.reload();
      return;
    }

    const response = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error("The new insight was generated, but the candidate view could not be refreshed.");
    sheetBody.innerHTML = await response.text();
    window.feather?.replace();
    window.refreshAdminCandidateSheetContent?.();
  }

  document.addEventListener("click", async event => {
    const definition = definitions.find(item =>
      event.target.closest?.(item.button)
    );
    if (!definition) return;

    const button = event.target.closest(definition.button);
    const mirror = button.closest("[data-admin-candidate-mirror]");
    const root = button.closest(definition.root);
    if (!mirror || !root || button.disabled || mirror.dataset.aiInsightGenerating === "true") return;

    event.preventDefault();
    event.stopPropagation();
    mirror.dataset.aiInsightGenerating = "true";
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    const swedish = isSwedish();
    showStatus(mirror, swedish
      ? `Skapar ${definition.label.sv}…`
      : `Generating ${definition.label.en}…`);

    try {
      await startAndWait(root);
      await refreshCandidate(mirror);
      const refreshedMirror = document.querySelector("#candidateSheetBody [data-admin-candidate-mirror]")
        || document.querySelector("[data-admin-candidate-mirror]");
      showStatus(refreshedMirror, swedish
        ? `AI-insikten har genererats och uppdaterats.`
        : "The AI insight has been generated and updated.");
    } catch (error) {
      console.error("Admin AI insight generation failed:", error);
      showStatus(mirror, error.message || (swedish
        ? "AI-insikten kunde inte genereras."
        : "The AI insight could not be generated."), true);
      button.disabled = false;
      button.removeAttribute("aria-busy");
      delete mirror.dataset.aiInsightGenerating;
    }
  });
})();
