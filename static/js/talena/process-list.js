(function () {
  const grid = document.getElementById("processGrid");

  if (!grid) {
    return;
  }

  const cards = Array.from(grid.querySelectorAll(".process-card"));
  const searchInput = document.getElementById("processSearch");
  const purposeFilter = document.getElementById("purposeFilter");
  const sortSelect = document.getElementById("sortBy");

  if (!searchInput || !purposeFilter || !sortSelect) {
    return;
  }

  const purposes = new Map();

  cards.forEach(function (card) {
    const label = (card.dataset.purpose || "").trim();

    if (label) {
      purposes.set(label.toLowerCase(), label);
    }
  });

  Array.from(purposes.values())
    .sort(function (a, b) {
      return a.localeCompare(b);
    })
    .forEach(function (label) {
      const option = document.createElement("option");
      option.value = label.toLowerCase();
      option.textContent = label;
      purposeFilter.appendChild(option);
    });

  // Restore the current list state after navigation, including pin/unpin POSTs.
  const initialParams = new URLSearchParams(window.location.search);
  const supportedSorts = Array.from(sortSelect.options).map(function (option) {
    return option.value;
  });
  if (supportedSorts.includes(initialParams.get("sort"))) {
    sortSelect.value = initialParams.get("sort");
  }
  searchInput.value = initialParams.get("q") || "";
  const initialPurpose = (initialParams.get("purpose") || "").toLowerCase();
  if (initialPurpose) {
    purposeFilter.value = initialPurpose;
  }

  function matches(card, query, purposeValue) {
    const haystack = [
      card.dataset.title || "",
      card.dataset.purposeLower || "",
      card.dataset.testsLower || "",
      card.dataset.labelsLower || "",
    ].join(" ");

    const filterMatches = (
      !purposeValue
      || (card.dataset.purposeLower || "") === purposeValue
    );

    const queryMatches = !query || haystack.includes(query);

    return filterMatches && queryMatches;
  }

  function sortCards(list, mode) {
    const copy = list.slice();

    const sortFunctions = {
      pinned_first: function (a, b) {
        const pinnedDifference = Number(b.dataset.pinned === "true")
          - Number(a.dataset.pinned === "true");
        if (pinnedDifference) {
          return pinnedDifference;
        }
        // Preserve the list's default newest-first ordering within each group.
        return (b.dataset.created || "").localeCompare(a.dataset.created || "");
      },
      created_desc: function (a, b) {
        return (b.dataset.created || "").localeCompare(a.dataset.created || "");
      },
      created_asc: function (a, b) {
        return (a.dataset.created || "").localeCompare(b.dataset.created || "");
      },
      candidates_desc: function (a, b) {
        return (
          parseInt(b.dataset.candidates || "0", 10)
          - parseInt(a.dataset.candidates || "0", 10)
        );
      },
      candidates_asc: function (a, b) {
        return (
          parseInt(a.dataset.candidates || "0", 10)
          - parseInt(b.dataset.candidates || "0", 10)
        );
      },
      title_asc: function (a, b) {
        return (a.dataset.title || "").localeCompare(b.dataset.title || "");
      },
      title_desc: function (a, b) {
        return (b.dataset.title || "").localeCompare(a.dataset.title || "");
      },
    };

    copy.sort(sortFunctions[mode] || function () {
      return 0;
    });

    return copy;
  }

  function syncListStateToUrl() {
    const url = new URL(window.location.href);
    const query = searchInput.value.trim();
    const purpose = purposeFilter.value.trim();
    const sort = sortSelect.value;

    if (query) url.searchParams.set("q", query);
    else url.searchParams.delete("q");
    if (purpose) url.searchParams.set("purpose", purpose);
    else url.searchParams.delete("purpose");
    if (sort && sort !== "created_desc") url.searchParams.set("sort", sort);
    else url.searchParams.delete("sort");

    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    grid.querySelectorAll("form[action*='toggle-pinned-project']").forEach(function (form) {
      const next = form.querySelector("input[name='next']");
      if (next) next.value = url.pathname + url.search;
    });
  }

  function render() {
    const query = (searchInput.value || "").trim().toLowerCase();
    const purposeValue = (purposeFilter.value || "").trim().toLowerCase();

    const visibleCards = sortCards(
      cards.filter(function (card) {
        return matches(card, query, purposeValue);
      }),
      sortSelect.value
    );

    cards.forEach(function (card) {
      card.classList.add("d-none");
    });

    visibleCards.forEach(function (card) {
      card.classList.remove("d-none");
      grid.appendChild(card);
    });

    syncListStateToUrl();
  }

  cards.forEach(function (card) {
    function openCard() {
      if (card.dataset.href) {
        window.location.href = card.dataset.href;
      }
    }

    card.addEventListener("click", function (event) {
      if (event.target.closest("a, button, form, input, select")) {
        return;
      }

      openCard();
    });

    card.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      if (event.target.closest("a, button, form, input, select")) {
        return;
      }

      event.preventDefault();
      openCard();
    });
  });

  // Reuse the Talena dialog for both archive and restore. Intercept only
  // when Bootstrap is available; native POST remains the no-JS fallback.
  const projectStatusModal = document.getElementById("projectStatusModal");
  const projectStatusForm = document.getElementById("projectStatusForm");
  const projectStatusName = document.getElementById("projectStatusName");

  if (projectStatusModal && projectStatusForm && projectStatusName) {
    grid.querySelectorAll("form[data-project-status-form]").forEach(function (sourceForm) {
      sourceForm.addEventListener("submit", function (event) {
        event.stopPropagation();
        if (!window.bootstrap || !window.bootstrap.Modal) return;

        event.preventDefault();
        const action = sourceForm.dataset.projectStatusAction === "restore"
          ? "restore" : "archive";

        projectStatusForm.action = sourceForm.action;
        projectStatusName.textContent = sourceForm.dataset.projectName || "";
        projectStatusModal.querySelectorAll("[data-project-status-copy]").forEach(function (element) {
          element.hidden = element.dataset.projectStatusCopy !== action;
        });
        window.bootstrap.Modal.getOrCreateInstance(projectStatusModal).show();
      });
    });
  }

  // Duplicate projects in one reusable Bootstrap modal. The form still posts
  // through Django's existing CSRF-protected endpoint and redirects on success.
  const duplicateModal = document.getElementById("duplicateProcessModal");
  const duplicateForm = document.getElementById("duplicateProcessForm");
  const duplicateName = document.getElementById("duplicateProcessName");
  const duplicateSource = document.getElementById("duplicateProcessSource");
  const duplicateSubmit = document.getElementById("duplicateProcessSubmit");

  if (duplicateModal && duplicateForm && duplicateName && duplicateSource) {
    duplicateModal.addEventListener("show.bs.modal", function (event) {
      const trigger = event.relatedTarget;
      if (!trigger || !trigger.matches("[data-duplicate-trigger]")) {
        return;
      }

      const sourceName = trigger.dataset.duplicateName || "";
      const suffix = duplicateModal.dataset.copySuffix || " (copy)";
      const allowedName = sourceName.slice(0, Math.max(0, 255 - suffix.length));

      duplicateForm.action = trigger.dataset.duplicateUrl || "";
      duplicateSource.textContent = sourceName;
      duplicateName.value = allowedName + suffix;
      if (duplicateSubmit) {
        duplicateSubmit.disabled = false;
      }
    });

    duplicateModal.addEventListener("shown.bs.modal", function () {
      duplicateName.focus();
      duplicateName.select();
    });

    duplicateForm.addEventListener("submit", function (event) {
      // Guard against an empty or whitespace-only name, including an edited
      // value that passes the browser's native "required" attribute.
      const name = duplicateName.value.trim();
      if (!name) {
        event.preventDefault();
        duplicateName.value = "";
        duplicateName.reportValidity();
        duplicateName.focus();
        return;
      }

      duplicateName.value = name;
      if (duplicateSubmit) {
        duplicateSubmit.disabled = true;
      }
    });
  }

  // One modal handles both safe permanent deletion and protected projects.
  const removeProjectModal = document.getElementById("removeProjectModal");
  if (removeProjectModal) {
    const removeForm = document.getElementById("removeProjectForm");
    const removeName = document.getElementById("removeProjectName");
    const removeSafe = document.getElementById("removeProjectSafe");
    const removeBlocked = document.getElementById("removeProjectBlocked");
    const removeSubmit = document.getElementById("removeProjectSubmit");

    removeProjectModal.addEventListener("show.bs.modal", function (event) {
      const trigger = event.relatedTarget;
      if (!trigger || !trigger.matches("[data-remove-project]")) return;
      const canDelete = trigger.dataset.canDelete === "true";
      removeForm.action = trigger.dataset.removeUrl || "";
      removeName.textContent = trigger.dataset.projectName || "";
      removeSafe.hidden = !canDelete;
      removeBlocked.hidden = canDelete;
      removeSubmit.hidden = !canDelete;
      removeSubmit.disabled = !canDelete;
    });
  }

  searchInput.addEventListener("input", render);
  purposeFilter.addEventListener("change", render);
  sortSelect.addEventListener("change", render);

  render();
})();
