(function () {
  "use strict";

  function installSafeFeatherRenderer() {
    if (!window.feather || !window.feather.icons) {
      return;
    }

    window.safeFeatherReplace = function (
      scope = document,
      globalAttributes = {}
    ) {
      const elements = Array.from(
        scope.querySelectorAll("[data-feather]")
      );

      elements.forEach(function (element) {
        const iconName = element.getAttribute("data-feather");
        const icon = window.feather.icons[iconName];

        if (!icon) {
          console.warn(`Unknown Feather icon: ${iconName}`, element);
          return;
        }

        try {
          const template = document.createElement("template");
          template.innerHTML = icon.toSvg().trim();

          const svg = template.content.firstElementChild;

          if (!(svg instanceof SVGElement)) {
            throw new Error(`Could not create SVG for icon "${iconName}".`);
          }

          Array.from(element.attributes).forEach(function (attribute) {
            if (attribute.name === "data-feather") {
              return;
            }

            if (attribute.name === "class") {
              const featherClasses = svg.getAttribute("class") || "";
              svg.setAttribute(
                "class",
                `${featherClasses} ${attribute.value}`.trim()
              );
              return;
            }

            svg.setAttribute(attribute.name, attribute.value);
          });

          Object.entries(globalAttributes || {}).forEach(function ([name, value]) {
            if (name === "class") {
              const existing = svg.getAttribute("class") || "";
              svg.setAttribute(
                "class",
                `${existing} ${value}`.trim()
              );
              return;
            }

            svg.setAttribute(name, String(value));
          });

          element.replaceWith(svg);
        } catch (error) {
          console.error(
            `Feather icon "${iconName}" could not be rendered:`,
            error,
            element
          );
        }
      });
    };

    window.feather.replace = function (attributes = {}) {
      window.safeFeatherReplace(document, attributes);
    };
  }

  window.openAppModal = function openAppModal({
    title,
    bodyHtml,
    footerHtml,
  } = {}) {
    const modalElement = document.getElementById("appModal");
    const titleElement = document.getElementById("appModalTitle");
    const bodyElement = document.getElementById("appModalBody");
    const footerElement = document.getElementById("appModalFooter");

    if (
      !modalElement
      || !titleElement
      || !bodyElement
      || !footerElement
      || !window.bootstrap
    ) {
      return;
    }

    const closeLabel = modalElement.dataset.closeLabel || "Close";

    titleElement.textContent = title || "Modal";
    bodyElement.innerHTML = bodyHtml || "";
    footerElement.innerHTML = footerHtml || `
      <button type="button" class="btn btn-light" data-bs-dismiss="modal">
        ${closeLabel}
      </button>
    `;

    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
  };

  window.copyToClipboard = async function copyToClipboard(text, statusElementId) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }

      if (statusElementId) {
        const statusElement = document.getElementById(statusElementId);

        if (statusElement) {
          statusElement.textContent = statusElement.dataset.copiedLabel || "Copied!";
          statusElement.classList.remove("text-muted");
          statusElement.classList.add("text-success");

          window.setTimeout(function () {
            statusElement.textContent = "";
          }, 2000);
        }
      }
    } catch (error) {
      console.error("Copy failed:", error);
    }
  };

  function initGlobalSearch() {
    const form = document.querySelector("[data-global-search]");
    const input = document.getElementById("globalSearchInput");
    const menu = document.getElementById("globalSearchDropdown");

    if (!form || !input || !menu) {
      return;
    }

    const searchUrl = form.dataset.searchUrl || "/search/";
    const noResultsLabel = form.dataset.noResultsLabel || "No results found";
    const typeLabels = {
      customer: form.dataset.customerLabel || "Customer",
      candidate: form.dataset.candidateLabel || "Candidate",
      process: form.dataset.processLabel || "Test process",
    };

    let timer = null;
    let lastQuery = "";
    let abortController = null;

    function hideMenu() {
      menu.classList.remove("show");
      menu.replaceChildren();
    }

    function showNoResults() {
      const item = document.createElement("span");
      item.className = "dropdown-item-text text-muted";
      item.textContent = noResultsLabel;
      menu.replaceChildren(item);
      menu.classList.add("show");
    }

    function showResults(results) {
      const fragment = document.createDocumentFragment();

      results.forEach(function (result) {
        const link = document.createElement("a");
        link.className = "dropdown-item d-flex align-items-center justify-content-between py-2";
        link.href = result.url || "#";

        const label = document.createElement("span");
        label.className = "fw-medium text-body";
        label.textContent = result.label || "";

        const tag = document.createElement("span");
        tag.className = "search-tag";
        tag.textContent = typeLabels[result.type] || "";

        link.append(label, tag);
        fragment.appendChild(link);
      });

      menu.replaceChildren(fragment);
      menu.classList.add("show");
    }

    async function runSearch(query) {
      if (abortController) {
        abortController.abort();
      }

      abortController = new AbortController();

      const separator = searchUrl.includes("?") ? "&" : "?";
      const response = await fetch(
        `${searchUrl}${separator}q=${encodeURIComponent(query)}`,
        {
          signal: abortController.signal,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        }
      );

      if (!response.ok) {
        return [];
      }

      const data = await response.json();
      return Array.isArray(data.results) ? data.results : [];
    }

    input.addEventListener("input", function () {
      const query = input.value.trim();

      if (query.length < 2) {
        lastQuery = "";
        hideMenu();
        return;
      }

      if (query === lastQuery) {
        return;
      }

      lastQuery = query;
      window.clearTimeout(timer);

      timer = window.setTimeout(async function () {
        try {
          const results = await runSearch(query);

          if (!results.length) {
            showNoResults();
            return;
          }

          showResults(results);
        } catch (error) {
          if (error.name !== "AbortError") {
            hideMenu();
          }
        }
      }, 180);
    });

    document.addEventListener("click", function (event) {
      if (!menu.contains(event.target) && event.target !== input) {
        hideMenu();
      }
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideMenu();
      }
    });
  }

  function initPersonalityMotivationInteractionSync() {
    document.addEventListener(
      "candidate-ai-content-updated",
      async function (event) {
        const eventTarget = event.target;

        if (!(eventTarget instanceof Element)) {
          return;
        }

        const root = eventTarget.closest(
          "[data-personality-ai-root]"
        );

        if (!root) {
          return;
        }

        const interactionElement = root.querySelector(
          "[data-personality-ai-motivation-interaction]"
        );

        const emptyElement = root.querySelector(
          "[data-personality-ai-motivation-interaction-empty]"
        );

        const streamUrl = root.dataset.streamUrl;

        if (
          !interactionElement
          || !streamUrl
          || root.dataset.personalityMotivationSyncing === "true"
        ) {
          return;
        }

        root.dataset.personalityMotivationSyncing = "true";

        try {
          const response = await fetch(
            streamUrl,
            {
              method: "GET",
              headers: {
                "Accept": "application/x-ndjson",
                "X-Requested-With": "XMLHttpRequest",
              },
              credentials: "same-origin",
            }
          );

          if (!response.ok) {
            return;
          }

          const responseText = await response.text();
          let motivationInteraction = "";

          responseText
            .split("\n")
            .map(function (line) {
              return line.trim();
            })
            .filter(Boolean)
            .forEach(function (line) {
              try {
                const streamEvent = JSON.parse(line);

                if (
                  streamEvent.type === "motivation_interaction"
                ) {
                  motivationInteraction = String(
                    streamEvent.text || ""
                  ).trim();
                }

                if (
                  streamEvent.type === "saved_result"
                  && streamEvent.data
                ) {
                  motivationInteraction = String(
                    streamEvent.data.motivation_interaction || ""
                  ).trim();
                }
              } catch (error) {
                // Ignore non-JSON lines in the defensive follow-up read.
              }
            });

          interactionElement.textContent = motivationInteraction;
          interactionElement.classList.toggle(
            "d-none",
            !motivationInteraction
          );

          emptyElement?.classList.toggle(
            "d-none",
            Boolean(motivationInteraction)
          );
        } catch (error) {
          console.warn(
            "Could not refresh personality and motivation interaction:",
            error
          );
        } finally {
          delete root.dataset.personalityMotivationSyncing;
        }
      }
    );
  }

  installSafeFeatherRenderer();

  function initialiseCustomerShell() {
    initGlobalSearch();
    initPersonalityMotivationInteractionSync();

    if (window.feather) {
      window.feather.replace();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialiseCustomerShell, {
      once: true,
    });
  } else {
    initialiseCustomerShell();
  }
})();
