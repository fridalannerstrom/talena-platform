/* Let admins generate missing interview-question sets in the read-only
 * customer mirror. Existing customer question sets are left untouched.
 */
(function () {
  "use strict";

  const sourceDefinitions = [
    {
      selector: "[data-personality-questions-root]",
      label: { sv: "Personlighet", en: "Personality" },
      requiresRoleContext: true,
    },
    {
      selector: "[data-motivation-questions-root]",
      label: { sv: "Motivation", en: "Motivation" },
    },
    {
      selector: "[data-cognitive-questions-root]",
      label: { sv: "Färdighet", en: "Skills" },
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

  function setStatus(root, message, isError = false) {
    const status = root.querySelector(
      "[data-pre-interview-questions-refresh-status]"
    );
    if (!status) return;
    status.textContent = message;
    status.hidden = !message;
    status.classList.toggle("text-danger", isError);
    status.classList.toggle("text-muted", !isError);
  }

  function readyMissingSources(mirror) {
    const swedish = isSwedish();
    return sourceDefinitions.flatMap(definition => {
      const source = mirror.querySelector(definition.selector);
      if (!source || source.dataset.hasResult === "true") return [];
      if (!source.dataset.regenerateUrl || !source.dataset.streamUrl) return [];
      if (definition.requiresRoleContext && source.dataset.roleContextAvailable !== "true") {
        return [];
      }
      if (source.dataset.status === "generating") return [];
      return [{
        source,
        regenerateUrl: source.dataset.regenerateUrl,
        streamUrl: source.dataset.streamUrl,
        label: definition.label[swedish ? "sv" : "en"],
      }];
    });
  }

  async function generateSource(item) {
    const csrfToken = getCookie("csrftoken");
    const resetResponse = await fetch(item.regenerateUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    });
    const resetData = await resetResponse.json();
    if (!resetResponse.ok) {
      throw new Error(resetData.error || "Could not start question generation.");
    }

    const streamResponse = await fetch(resetData.stream_url || item.streamUrl, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    const body = await streamResponse.text();
    if (!streamResponse.ok) {
      let message = "Question generation failed.";
      try {
        message = JSON.parse(body).error || message;
      } catch (_) {}
      throw new Error(message);
    }

    let finished = false;
    for (const line of body.split(/\r?\n/).filter(Boolean)) {
      let event;
      try {
        event = JSON.parse(line);
      } catch (_) {
        continue;
      }
      if (event.type === "error") {
        throw new Error(event.message || "Question generation failed.");
      }
      if (event.type === "done" || event.type === "saved_result") {
        finished = true;
      }
    }
    if (!finished) throw new Error("Question generation did not finish.");
  }

  async function refreshQuestions(root) {
    const response = await fetch(root.dataset.refreshUrl, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error("Could not refresh the question list.");

    const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
    const updatedRoot = parsed.querySelector("[data-combined-questions-root]");
    if (!updatedRoot) throw new Error("The updated question list was not returned.");
    root.replaceWith(updatedRoot);
    window.feather?.replace();
    return updatedRoot;
  }

  document.addEventListener("click", async event => {
    const button = event.target.closest?.(
      "[data-pre-interview-questions-regenerate]"
    );
    if (!button) return;

    const mirror = button.closest("[data-admin-candidate-mirror]");
    if (!mirror || button.disabled) return;

    event.preventDefault();
    event.stopPropagation();

    const root = button.closest("[data-combined-questions-root]");
    const sources = readyMissingSources(mirror);
    const swedish = isSwedish();
    if (!root) return;
    if (!sources.length) {
      setStatus(root, swedish
        ? "Inga saknade frågeset kunde skapas. Kontrollera att testresultat och rollkontext finns."
        : "No missing question sets could be generated. Check that assessment results and role context are available.", true);
      return;
    }

    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    const failures = [];
    let activeRoot = root;
    try {
      for (const item of sources) {
        setStatus(activeRoot, swedish
          ? `Skapar frågor för ${item.label}…`
          : `Generating ${item.label} questions…`);
        try {
          await generateSource(item);
        } catch (error) {
          console.error(`Admin question generation failed for ${item.label}:`, error);
          failures.push(item.label);
        }
      }

      activeRoot = await refreshQuestions(activeRoot);
      setStatus(activeRoot, failures.length
        ? (swedish
          ? `Frågor kunde inte skapas för: ${failures.join(", ")}.`
          : `Questions could not be generated for: ${failures.join(", ")}.`)
        : (swedish
          ? "Saknade intervjufrågor har skapats."
          : "Missing interview questions have been generated."), failures.length > 0);
    } catch (error) {
      console.error("Admin interview-question refresh failed:", error);
      setStatus(activeRoot, error.message || (swedish
        ? "Intervjufrågorna kunde inte uppdateras."
        : "Interview questions could not be refreshed."), true);
    } finally {
      const currentButton = activeRoot.querySelector(
        "[data-pre-interview-questions-regenerate]"
      );
      if (currentButton) {
        currentButton.disabled = false;
        currentButton.removeAttribute("aria-busy");
      }
    }
  });
})();
