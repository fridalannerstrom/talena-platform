(function () {
  "use strict";

  const ROOT_SELECTOR = "[data-personality-questions-root]";
  const COMPETENCY_PREFIX = "competency::";
  const MAX_TRAIT_SELECTION = 8;
  const MAX_COMPETENCY_SELECTION = 6;

  function roots(container) {
    const result = [];
    if (container && container.matches && container.matches(ROOT_SELECTOR)) {
      result.push(container);
    }
    if (container && container.querySelectorAll) {
      container.querySelectorAll(ROOT_SELECTOR).forEach((root) => result.push(root));
    }
    return result;
  }

  function optionBasis(checkbox) {
    return checkbox.dataset.questionBasisOption ||
      (String(checkbox.value || "").startsWith(COMPETENCY_PREFIX)
        ? "competencies"
        : "traits");
  }

  function selectionLimit(mode) {
    return mode === "competencies"
      ? MAX_COMPETENCY_SELECTION
      : MAX_TRAIT_SELECTION;
  }

  function optionCheckboxes(root) {
    return Array.from(
      root.querySelectorAll("[data-personality-trait-checkbox]")
    );
  }

  function checkedOptions(root, mode) {
    return optionCheckboxes(root).filter((checkbox) => {
      return checkbox.checked && (!mode || optionBasis(checkbox) === mode);
    });
  }

  function clearOtherModeSelections(root, mode) {
    optionCheckboxes(root).forEach((checkbox) => {
      if (optionBasis(checkbox) === mode || !checkbox.checked) {
        return;
      }

      checkbox.checked = false;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  function unlockOptionInputs(root) {
    optionCheckboxes(root).forEach((checkbox) => {
      checkbox.disabled = false;
    });
  }

  function isSwedish() {
    return String(document.documentElement.lang || "sv")
      .toLowerCase()
      .startsWith("sv");
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith(`${name}=`));

    return cookieValue
      ? decodeURIComponent(cookieValue.split("=")[1])
      : null;
  }

  function updateQuestionsIntro(root) {
    const intro = root.querySelector(
      ".personality-questions-header p.text-muted.small"
    );

    if (!intro) {
      return;
    }

    intro.textContent = isSwedish()
      ? "Utforska relevanta beteenden genom praktiska, syftesanpassade intervjufrågor."
      : "Explore relevant behaviours through practical, purpose-aware interview questions.";
  }

  function focusLabelMap(root) {
    const labelMap = new Map();

    root.querySelectorAll("[data-personality-trait-checkbox]").forEach((checkbox) => {
      const explicitLabel = checkbox.dataset.questionFocusLabel;
      if (explicitLabel) {
        labelMap.set(String(checkbox.value || "").trim(), explicitLabel);
      }
    });

    return labelMap;
  }

  function localiseRenderedFocusLabels(root) {
    const labelMap = focusLabelMap(root);

    root.querySelectorAll(
      "[data-personality-selected-traits] .personality-trait-pill, " +
      ".personality-question-card__traits span"
    ).forEach((element) => {
      const rawValue = String(element.textContent || "").trim();
      const label = labelMap.get(rawValue);
      if (label && element.textContent !== label) {
        element.textContent = label;
      }
    });
  }

  function activeMode(root) {
    return root.dataset.questionBasis === "competencies"
      ? "competencies"
      : "traits";
  }

  function selectedMode(root) {
    const checked = Array.from(
      root.querySelectorAll("[data-personality-trait-checkbox]:checked")
    );

    return checked.some((checkbox) => optionBasis(checkbox) === "competencies")
      ? "competencies"
      : "traits";
  }

  function modeButton(root, mode) {
    return root.querySelector(
      `[data-question-basis-tab="${mode}"]`
    );
  }

  function updateTraitLimitCopy(root) {
    const traitButton = modeButton(root, "traits");
    if (!traitButton) {
      return;
    }

    if (isSwedish()) {
      traitButton.dataset.dialogDescription =
        "Välj upp till åtta personlighetsdrag, eller lämna alla omarkerade för att låta Talena välja utifrån processens syfte och kontext.";
      traitButton.dataset.statusLabel = "Välj upp till 8 personlighetsdrag";
    } else {
      traitButton.dataset.dialogDescription =
        "Choose up to eight traits, or leave all traits unselected to let Talena choose based on the process purpose and context.";
      traitButton.dataset.statusLabel = "Select up to 8 traits";
    }
  }

  function updateSelectionLimitState(root) {
    if (!root) {
      return;
    }

    // The legacy inline controller still knows about the old six-item cap.
    // Undo that disabled state here and apply the current basis-specific cap.
    unlockOptionInputs(root);

    const mode = activeMode(root);
    const count = checkedOptions(root, mode).length;
    const limit = selectionLimit(mode);
    const countElement = root.querySelector("[data-personality-traits-count]");
    const saveButton = root.querySelector("[data-personality-traits-save]");

    if (countElement) {
      if (isSwedish()) {
        countElement.textContent = `${count} ${count === 1 ? "vald" : "valda"}`;
      } else {
        countElement.textContent = `${count} selected`;
      }
    }

    if (saveButton) {
      saveButton.disabled = count > limit;
    }

    root.classList.toggle(
      "personality-question-basis-at-limit",
      count >= limit
    );
  }

  function updateModeCopy(root, mode) {
    const button = modeButton(root, mode);
    if (!button) {
      return;
    }

    const summaryTitle = root.querySelector("[data-question-basis-summary-title]");
    const summaryDescription = root.querySelector("[data-question-basis-summary-description]");
    const editLabel = root.querySelector("[data-question-basis-edit-label]");
    const dialogTitle = root.querySelector("[data-question-basis-dialog-title]");
    const dialogDescription = root.querySelector("[data-question-basis-dialog-description]");
    const statusLabel = root.querySelector("[data-question-basis-status-label]");
    const emptyError = root.querySelector("[data-question-basis-empty-error]");

    if (summaryTitle && button.dataset.summaryTitle) {
      summaryTitle.textContent = button.dataset.summaryTitle;
    }
    if (summaryDescription && button.dataset.summaryDescription) {
      summaryDescription.textContent = button.dataset.summaryDescription;
    }
    if (editLabel && button.dataset.editLabel) {
      editLabel.textContent = button.dataset.editLabel;
    }
    if (dialogTitle && button.dataset.dialogTitle) {
      dialogTitle.textContent = button.dataset.dialogTitle;
    }
    if (dialogDescription && button.dataset.dialogDescription) {
      dialogDescription.textContent = button.dataset.dialogDescription;
    }
    if (statusLabel && button.dataset.statusLabel) {
      statusLabel.textContent = button.dataset.statusLabel;
    }
    if (emptyError) {
      emptyError.hidden = true;
    }
  }

  function setMode(root, mode) {
    if (!root || !["traits", "competencies"].includes(mode)) {
      return;
    }

    root.dataset.questionBasis = mode;

    root.querySelectorAll("[data-question-basis-tab]").forEach((button) => {
      const isActive = button.dataset.questionBasisTab === mode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
    });

    root.querySelectorAll("[data-question-basis-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.questionBasisPanel !== mode;
    });

    updateModeCopy(root, mode);
    updateSelectionLimitState(root);
    localiseRenderedFocusLabels(root);
  }

  function syncModeToSavedSelection(root) {
    if (!root) {
      return;
    }

    setMode(root, selectedMode(root));
    updateSelectionLimitState(root);
  }

  async function saveExpandedTraitSelection(root, selectedOptions) {
    const updateUrl = root.dataset.updateTraitsUrl;
    const editor = root.querySelector("[data-personality-traits-editor]");
    const saveButton = root.querySelector("[data-personality-traits-save]");
    const cancelButtons = root.querySelectorAll("[data-personality-traits-cancel]");
    const regenerateButton = root.querySelector("[data-personality-questions-regenerate]");
    const errorBox = root.querySelector("[data-personality-questions-error]");

    if (!updateUrl) {
      return;
    }

    const selectedTraits = selectedOptions.map((checkbox) => checkbox.value);

    if (saveButton) {
      saveButton.disabled = true;
    }
    cancelButtons.forEach((button) => {
      button.disabled = true;
    });

    try {
      const response = await fetch(updateUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        body: JSON.stringify({ traits: selectedTraits }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error ||
          (window.TALENA_PROCESS_I18N &&
            window.TALENA_PROCESS_I18N.traitSelectionCouldNotBeSaved) ||
          "The trait selection could not be saved."
        );
      }

      const savedTraits = Array.isArray(data.selected_traits)
        ? data.selected_traits
        : selectedTraits;
      const savedKeys = new Set(savedTraits.map((item) => String(item).trim()));

      optionCheckboxes(root).forEach((checkbox) => {
        checkbox.checked = savedKeys.has(String(checkbox.value || "").trim());
      });

      if (editor) {
        if (typeof editor.close === "function") {
          editor.close();
        } else {
          editor.removeAttribute("open");
        }
      }

      // Reuse the existing regeneration flow after the expanded selection has
      // been saved. The stream will refresh selected pills, questions and labels.
      if (regenerateButton) {
        regenerateButton.click();
      }
    } catch (error) {
      console.error("Expanded personality trait selection error:", error);

      if (errorBox) {
        errorBox.classList.remove("d-none");
        errorBox.textContent = error.message || "The trait selection could not be saved.";
      }
    } finally {
      if (saveButton) {
        saveButton.disabled = false;
      }
      cancelButtons.forEach((button) => {
        button.disabled = false;
      });
      updateSelectionLimitState(root);
    }
  }

  function initialiseRoot(root) {
    if (!root || root.dataset.questionBasisUiInitialised === "true") {
      return;
    }

    root.dataset.questionBasisUiInitialised = "true";
    updateTraitLimitCopy(root);
    setMode(root, activeMode(root));
    updateQuestionsIntro(root);
    updateSelectionLimitState(root);

    const observer = new MutationObserver(() => {
      localiseRenderedFocusLabels(root);
    });

    observer.observe(root, {
      childList: true,
      subtree: true,
    });

    localiseRenderedFocusLabels(root);
  }

  function initialiseWithin(container) {
    roots(container).forEach(initialiseRoot);
  }

  // Keep all choices usable while enforcing a basis-specific selection cap:
  // eight personality traits or six competencies.
  document.addEventListener("click", function (event) {
    const option = event.target.closest(".personality-trait-option");
    const checkbox = option
      ? option.querySelector("[data-personality-trait-checkbox]")
      : event.target.closest("[data-personality-trait-checkbox]");

    if (!checkbox || checkbox.checked) {
      return;
    }

    const root = checkbox.closest(ROOT_SELECTOR);
    if (!root) {
      return;
    }

    const mode = optionBasis(checkbox);
    if (mode !== activeMode(root)) {
      return;
    }

    if (checkedOptions(root, mode).length < selectionLimit(mode)) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    unlockOptionInputs(root);
  }, true);

  document.addEventListener("click", function (event) {
    const tab = event.target.closest("[data-question-basis-tab]");
    if (tab) {
      const root = tab.closest(ROOT_SELECTOR);
      const mode = tab.dataset.questionBasisTab;
      setMode(root, mode);
      return;
    }

    const editorAction = event.target.closest(
      "[data-personality-traits-edit], [data-personality-traits-cancel]"
    );

    if (editorAction) {
      const root = editorAction.closest(ROOT_SELECTOR);
      window.setTimeout(() => {
        syncModeToSavedSelection(root);
        updateSelectionLimitState(root);
      }, 0);
    }
  });

  // Capture before the legacy six-item save handler. Selections 0-6 can use
  // the existing flow unchanged; trait selections 7-8 use the expanded save
  // flow here so the old guard cannot silently discard the click.
  document.addEventListener("click", function (event) {
    const saveButton = event.target.closest("[data-personality-traits-save]");
    if (!saveButton) {
      return;
    }

    const root = saveButton.closest(ROOT_SELECTOR);
    if (!root) {
      return;
    }

    const mode = activeMode(root);
    const selectedActiveOptions = checkedOptions(root, mode);

    if (mode === "competencies" && !selectedActiveOptions.length) {
      event.preventDefault();
      event.stopImmediatePropagation();

      const emptyError = root.querySelector("[data-question-basis-empty-error]");
      if (emptyError) {
        emptyError.hidden = false;
        emptyError.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      return;
    }

    optionCheckboxes(root).forEach((checkbox) => {
      if (optionBasis(checkbox) !== mode && checkbox.checked) {
        checkbox.checked = false;
      }
    });

    if (
      mode === "traits" &&
      selectedActiveOptions.length > MAX_COMPETENCY_SELECTION &&
      selectedActiveOptions.length <= MAX_TRAIT_SELECTION
    ) {
      event.preventDefault();
      event.stopImmediatePropagation();
      void saveExpandedTraitSelection(root, selectedActiveOptions);
    }
  }, true);

  document.addEventListener("change", function (event) {
    const checkbox = event.target.closest("[data-personality-trait-checkbox]");
    if (!checkbox) {
      return;
    }

    const root = checkbox.closest(ROOT_SELECTOR);
    if (!root) {
      return;
    }

    const mode = optionBasis(checkbox);

    if (checkbox.checked) {
      if (activeMode(root) !== mode) {
        setMode(root, mode);
      }

      clearOtherModeSelections(root, mode);
    }

    const emptyError = root.querySelector("[data-question-basis-empty-error]");
    if (emptyError && checkbox.checked) {
      emptyError.hidden = true;
    }

    // Runs after the existing checkbox change listener, undoing its legacy
    // six-item disabled state and restoring the current limit/save state.
    updateSelectionLimitState(root);
  });

  document.addEventListener("DOMContentLoaded", function () {
    initialiseWithin(document);
  });

  const documentObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          initialiseWithin(node);
        }
      });
    });
  });

  documentObserver.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();