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

  function initTeamStyleRankBars() {
    const rows = document.querySelectorAll(
      ".talena-team-page .team-style-rank-row"
    );

    rows.forEach(function (row) {
      const fill = row.querySelector(".team-style-bar-fill");
      const score = row.querySelector(".team-style-rank-score");

      if (!fill || !score) {
        return;
      }

      const scoreText = (score.textContent || "")
        .trim()
        .replace(",", ".");
      const match = scoreText.match(/([0-9]+(?:\.[0-9]+)?)\s*\/\s*5/);

      if (!match) {
        fill.style.width = "0%";
        fill.classList.add("is-empty");
        return;
      }

      const value = Number.parseFloat(match[1]);

      if (!Number.isFinite(value)) {
        fill.style.width = "0%";
        fill.classList.add("is-empty");
        return;
      }

      const clampedValue = Math.max(0, Math.min(5, value));
      const percent = (clampedValue / 5) * 100;

      fill.style.width = `${percent}%`;
      fill.classList.remove("is-empty");
      fill.setAttribute("aria-hidden", "true");
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

  function getTeamStyleLabelMap(chartElement) {
    return {
      Connector: chartElement.dataset.styleConnector || "Connector",
      Catalyst: chartElement.dataset.styleCatalyst || "Catalyst",
      Director: chartElement.dataset.styleDirector || "Director",
      Energiser: chartElement.dataset.styleEnergiser || "Energiser",
      Architect: chartElement.dataset.styleArchitect || "Architect",
      Harmoniser: chartElement.dataset.styleHarmoniser || "Harmoniser",
      Analyst: chartElement.dataset.styleAnalyst || "Analyst",
      Auditor: chartElement.dataset.styleAuditor || "Auditor"
    };
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

    const styleLabelMap = getTeamStyleLabelMap(chartElement);
    const displayLabels = labels.map(function (label) {
      return styleLabelMap[label] || label;
    });

    const averageLabel = chartElement.dataset.averageLabel || "Average";
    const maximumLabel = chartElement.dataset.maximumLabel || "Maximum";

    new window.Chart(chartElement, {
      type: "radar",
      data: {
        labels: displayLabels,
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
            pointHoverRadius: 4,
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
            pointHoverRadius: 3.5,
            borderWidth: 1.5,
            borderDash: [5, 4],
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "nearest"
        },
        scales: {
          r: {
            min: 0,
            max: 5,
            angleLines: {
              color: "rgba(117, 105, 99, 0.10)"
            },
            grid: {
              color: "rgba(117, 105, 99, 0.10)"
            },
            pointLabels: {
              color: "#6F6762",
              padding: 10,
              font: {
                size: 10,
                weight: 600
              }
            },
            ticks: {
              display: false,
              stepSize: 1
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
          },
          tooltip: {
            displayColors: true,
            padding: 10,
            callbacks: {
              label: function (context) {
                return `${context.dataset.label}: ${context.formattedValue} / 5`;
              }
            }
          }
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCandidateSearch();
    initTeamStyleRankBars();
    initTeamStyleChart();
  });
})();