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

  grid.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.stopPropagation();

      const message = form.dataset.confirm || "";

      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  searchInput.addEventListener("input", render);
  purposeFilter.addEventListener("change", render);
  sortSelect.addEventListener("change", render);

  render();
})();
