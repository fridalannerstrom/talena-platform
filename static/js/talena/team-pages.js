(function () {
  "use strict";

  function initCandidateSearch() {
    const searchInput = document.getElementById("candidateSearch");
    const table = document.getElementById("candidateTable");

    if (!searchInput || !table) {
      return;
    }

    searchInput.addEventListener("input", function () {
      const query = searchInput.value.trim().toLowerCase();
      const rows = table.querySelectorAll("tbody tr");

      rows.forEach(function (row) {
        row.style.display = row.innerText.toLowerCase().includes(query)
          ? ""
          : "none";
      });
    });
  }

  function readJsonScript(id) {
    const element = document.getElementById(id);

    if (!element) {
      return [];
    }

    try {
      return JSON.parse(element.textContent || "[]");
    } catch (error) {
      console.warn(`Could not parse ${id}.`, error);
      return [];
    }
  }

  function initTeamStyleChart() {
    const chartElement = document.getElementById("teamStyleAverageChart");

    if (!chartElement || typeof window.Chart === "undefined") {
      return;
    }

    const labels = readJsonScript("team-style-chart-labels");
    const averageValues = readJsonScript("team-style-chart-averages");
    const maxValues = readJsonScript("team-style-chart-max");

    if (!labels.length) {
      return;
    }

    const averageLabel = chartElement.dataset.averageLabel || "Average";
    const maximumLabel = chartElement.dataset.maximumLabel || "Maximum";

    new window.Chart(chartElement, {
      type: "radar",
      data: {
        labels: labels,
        datasets: [
          {
            label: averageLabel,
            data: averageValues,
            borderColor: "#FF6F61",
            backgroundColor: "rgba(255, 111, 97, 0.11)",
            pointBackgroundColor: "#FF6F61",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 3,
            borderWidth: 2,
            fill: true
          },
          {
            label: maximumLabel,
            data: maxValues,
            borderColor: "#8FAF98",
            backgroundColor: "rgba(143, 175, 152, 0.03)",
            pointBackgroundColor: "#8FAF98",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 2.5,
            borderWidth: 1.5,
            borderDash: [5, 4],
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 10,
            angleLines: {
              color: "rgba(117, 105, 99, 0.10)"
            },
            grid: {
              color: "rgba(117, 105, 99, 0.10)"
            },
            pointLabels: {
              color: "#6F6762",
              font: {
                size: 10,
                weight: 600
              }
            },
            ticks: {
              display: false,
              stepSize: 2
            }
          }
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: "#6F6762",
              boxWidth: 12,
              boxHeight: 12,
              usePointStyle: true,
              pointStyle: "circle",
              padding: 18,
              font: {
                size: 10,
                weight: 600
              }
            }
          }
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCandidateSearch();
    initTeamStyleChart();
  });
})();
