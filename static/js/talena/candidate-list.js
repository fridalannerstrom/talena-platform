(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("candidateSearch");
    const table = document.querySelector("[data-candidate-directory-table]");

    if (!searchInput || !table) {
      return;
    }

    const rows = Array.from(
      table.querySelectorAll("tbody tr[data-candidate-row]")
    );

    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim().toLowerCase();

      rows.forEach((row) => {
        const matches = row.innerText.toLowerCase().includes(query);
        row.hidden = !matches;
      });
    });
  });
})();
