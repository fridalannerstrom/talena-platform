(function () {
  "use strict";

  function isSwedish() {
    return (document.documentElement.lang || "")
      .toLowerCase()
      .startsWith("sv");
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

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

  function parseScoreOutOfFive(value) {
    const normalized = String(value || "")
      .trim()
      .replace(",", ".");
    const match = normalized.match(/([0-9]+(?:\.[0-9]+)?)\s*\/\s*5/);

    if (!match) {
      return null;
    }

    const parsed = Number.parseFloat(match[1]);

    if (!Number.isFinite(parsed)) {
      return null;
    }

    return Math.max(0, Math.min(5, parsed));
  }

  function parseBareScore(value) {
    const normalized = String(value || "")
      .trim()
      .replace(",", ".");
    const match = normalized.match(/([0-9]+(?:\.[0-9]+)?)/);

    if (!match) {
      return null;
    }

    const parsed = Number.parseFloat(match[1]);
    if (!Number.isFinite(parsed)) {
      return null;
    }

    return Math.max(0, Math.min(5, parsed));
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

      const value = parseScoreOutOfFive(score.textContent || "");

      if (value === null) {
        fill.style.width = "0%";
        fill.classList.add("is-empty");
        return;
      }

      const percent = (value / 5) * 100;

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

  function readTeamStyleMinimumValues(expectedCount) {
    const tables = document.querySelectorAll(
      ".talena-team-page .team-table"
    );

    for (const table of tables) {
      const headers = table.querySelectorAll("thead th");
      const rows = table.querySelectorAll("tbody tr");

      if (headers.length !== 3 || rows.length !== expectedCount) {
        continue;
      }

      const values = Array.from(rows).map(function (row) {
        const cells = row.querySelectorAll("td");

        if (cells.length < 3) {
          return null;
        }

        return parseScoreOutOfFive(cells[2].textContent || "");
      });

      if (
        values.length === expectedCount
        && values.every(function (value) { return value !== null; })
      ) {
        return values;
      }
    }

    return [];
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

    const minimumValues = readTeamStyleMinimumValues(labels.length);
    const styleLabelMap = getTeamStyleLabelMap(chartElement);
    const displayLabels = labels.map(function (label) {
      return styleLabelMap[label] || label;
    });

    const averageLabel = chartElement.dataset.averageLabel || "Average";
    const minimumLabel = chartElement.dataset.minimumLabel || "Minimum";
    const maximumLabel = chartElement.dataset.maximumLabel || "Maximum";

    const datasets = [
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
      }
    ];

    if (minimumValues.length === labels.length) {
      datasets.push({
        label: minimumLabel,
        data: minimumValues,
        borderColor: "#B7A99E",
        backgroundColor: "rgba(183, 169, 158, 0.02)",
        pointBackgroundColor: "#B7A99E",
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2,
        pointRadius: 2.5,
        pointHoverRadius: 3.5,
        borderWidth: 1.5,
        borderDash: [2, 4],
        fill: false
      });
    }

    datasets.push({
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
    });

    new window.Chart(chartElement, {
      type: "radar",
      data: {
        labels: displayLabels,
        datasets: datasets
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

  function initTeamModelGuide() {
    const chartElement = document.getElementById("teamStyleAverageChart");
    const analyticsCard = chartElement && chartElement.closest(".card");

    if (!analyticsCard || document.querySelector(".team-model-guide-card")) {
      return;
    }

    const sv = isSwedish();
    const copy = sv
      ? {
          eyebrow: "OM MODELLEN",
          title: "Så tolkar du teamrapporten",
          intro: "Teamstilarna beskriver hur olika preferenser kan bidra till hur ett team utforskar, leder, levererar och kritiskt granskar. Använd rapporten som stöd för reflektion och samtal, inte som fasta etiketter eller mått på förmåga.",
          open: "Läs om modellen",
          quadrants: [
            ["Utforska", "Nätverkande, nya perspektiv och idéer. Här syns preferenser för att skapa kontakter och utmana etablerade sätt att tänka."],
            ["Leda", "Samordning, riktning och energi. Här syns preferenser för att fatta beslut, påverka och driva teamets arbete framåt."],
            ["Leverera", "Planering, genomförande och samarbete. Här syns preferenser för att skapa struktur och hjälpa teamet att få saker gjorda tillsammans."],
            ["Kritiskt granska", "Analys, kvalitet och uppföljning. Här syns preferenser för att pröva idéer, upptäcka risker och säkerställa att åtaganden håller."]
          ]
        }
      : {
          eyebrow: "ABOUT THE MODEL",
          title: "How to interpret the team report",
          intro: "Team styles describe how different preferences may contribute to the way a team explores, directs, delivers and critically reviews its work. Use the report as a basis for reflection and discussion, not as fixed labels or measures of ability.",
          open: "Read about the model",
          quadrants: [
            ["Exploring", "Networking, new perspectives and ideas. This area reflects preferences for building connections and challenging established ways of thinking."],
            ["Directing", "Coordination, direction and energy. This area reflects preferences for making decisions, influencing and driving the team's work forward."],
            ["Delivering", "Planning, implementation and collaboration. This area reflects preferences for creating structure and helping the team turn plans into action."],
            ["Critiquing", "Analysis, quality and follow-through. This area reflects preferences for testing ideas, spotting risks and making sure commitments hold up."]
          ]
        };

    const quadrantHtml = copy.quadrants.map(function (item) {
      return `
        <div class="team-model-quadrant">
          <div class="team-model-quadrant-title">${escapeHtml(item[0])}</div>
          <p>${escapeHtml(item[1])}</p>
        </div>
      `;
    }).join("");

    const wrapper = document.createElement("div");
    wrapper.className = "card mb-4 team-model-guide-card";
    wrapper.innerHTML = `
      <details class="team-model-guide">
        <summary>
          <div>
            <div class="team-guide-eyebrow"><span></span>${escapeHtml(copy.eyebrow)}</div>
            <div class="team-guide-title">${escapeHtml(copy.title)}</div>
            <p class="team-guide-intro">${escapeHtml(copy.intro)}</p>
          </div>
          <div class="team-guide-toggle">
            <span>${escapeHtml(copy.open)}</span>
            <span class="team-guide-chevron" aria-hidden="true">⌄</span>
          </div>
        </summary>
        <div class="team-model-guide-body">
          <div class="team-model-quadrant-grid">${quadrantHtml}</div>
        </div>
      </details>
    `;

    analyticsCard.parentNode.insertBefore(wrapper, analyticsCard);
  }

  function createMemberRadar(canvas, labels, values) {
    if (!canvas || canvas.dataset.chartReady === "true") {
      return;
    }

    if (typeof window.Chart === "undefined") {
      return;
    }

    canvas.dataset.chartReady = "true";

    new window.Chart(canvas, {
      type: "radar",
      data: {
        labels: labels,
        datasets: [
          {
            data: values,
            borderColor: "#FF6F61",
            backgroundColor: "rgba(255, 111, 97, 0.12)",
            pointBackgroundColor: "#FF6F61",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 2.5,
            pointHoverRadius: 3.5,
            borderWidth: 2,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 5,
            angleLines: { color: "rgba(117, 105, 99, 0.10)" },
            grid: { color: "rgba(117, 105, 99, 0.10)" },
            pointLabels: {
              color: "#6F6762",
              padding: 7,
              font: { size: 9, weight: 600 }
            },
            ticks: { display: false, stepSize: 1 }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            callbacks: {
              label: function (context) {
                return `${context.formattedValue} / 5`;
              }
            }
          }
        }
      }
    });
  }

  function initTeamMemberProfiles() {
    const memberHeader = document.querySelector(
      ".talena-team-page .team-table .team-member-column"
    );
    const table = memberHeader && memberHeader.closest("table");
    const card = table && table.closest(".card");
    const body = card && card.querySelector(".card-body");

    if (!table || !card || !body || body.dataset.enhancedProfiles === "true") {
      return;
    }

    const sv = isSwedish();
    const strings = sv
      ? {
          open: "Visa profil",
          close: "Dölj profil",
          ranked: "Rangordnade teamstilar",
          chart: "Individuell profil",
          noData: "Ingen teamstilsdata tillgänglig"
        }
      : {
          open: "View profile",
          close: "Hide profile",
          ranked: "Ranked team styles",
          chart: "Individual profile",
          noData: "No team style data available"
        };

    const headers = Array.from(table.querySelectorAll("thead th"))
      .slice(1)
      .map(function (header) { return header.textContent.trim(); });
    const rows = Array.from(table.querySelectorAll("tbody tr"));

    if (!headers.length || !rows.length) {
      return;
    }

    const list = document.createElement("div");
    list.className = "team-member-profile-list";

    rows.forEach(function (row, index) {
      const cells = Array.from(row.querySelectorAll("td"));
      if (cells.length < 2) {
        return;
      }

      const initials = (
        cells[0].querySelector(".team-member-initials")?.textContent || "?"
      ).trim();
      const name = (
        cells[0].querySelector(".fw-semibold")?.textContent || ""
      ).trim();
      const email = (
        cells[0].querySelector(".text-muted")?.textContent || ""
      ).trim();
      const values = cells.slice(1).map(function (cell) {
        return parseBareScore(cell.textContent || "");
      });
      const hasData = values.some(function (value) { return value !== null; });

      const ranked = headers.map(function (label, styleIndex) {
        return {
          label: label,
          value: values[styleIndex]
        };
      }).filter(function (item) {
        return item.value !== null;
      }).sort(function (a, b) {
        return b.value - a.value;
      });

      const rankedHtml = ranked.map(function (item) {
        const width = Math.max(0, Math.min(100, (item.value / 5) * 100));
        return `
          <div class="team-member-style-row">
            <div class="team-member-style-label">${escapeHtml(item.label)}</div>
            <div class="team-member-style-track">
              <div class="team-member-style-fill" style="width:${width}%"></div>
            </div>
            <div class="team-member-style-score">${item.value} / 5</div>
          </div>
        `;
      }).join("");

      const details = document.createElement("details");
      details.className = "team-member-profile-item";
      details.innerHTML = `
        <summary>
          <div class="team-member-profile-person">
            <div class="team-member-initials">${escapeHtml(initials)}</div>
            <div>
              <div class="team-member-profile-name">${escapeHtml(name)}</div>
              <div class="team-member-profile-email">${escapeHtml(email)}</div>
            </div>
          </div>
          <div class="team-member-profile-action">
            <span class="team-member-profile-action-label">${escapeHtml(strings.open)}</span>
            <span class="team-guide-chevron" aria-hidden="true">⌄</span>
          </div>
        </summary>
        <div class="team-member-profile-body">
          ${hasData ? `
            <div class="team-member-profile-chart-panel">
              <div class="team-member-profile-subtitle">${escapeHtml(strings.chart)}</div>
              <div class="team-member-radar-wrap">
                <canvas class="team-member-radar" id="team-member-radar-${index}"></canvas>
              </div>
            </div>
            <div class="team-member-profile-ranking-panel">
              <div class="team-member-profile-subtitle">${escapeHtml(strings.ranked)}</div>
              <div class="team-member-style-ranking">${rankedHtml}</div>
            </div>
          ` : `
            <div class="team-member-profile-empty">${escapeHtml(strings.noData)}</div>
          `}
        </div>
      `;

      details._teamStyleLabels = headers;
      details._teamStyleValues = values.map(function (value) {
        return value === null ? 0 : value;
      });

      details.addEventListener("toggle", function () {
        const action = details.querySelector(".team-member-profile-action-label");
        if (action) {
          action.textContent = details.open ? strings.close : strings.open;
        }

        if (details.open && hasData) {
          window.requestAnimationFrame(function () {
            createMemberRadar(
              details.querySelector(".team-member-radar"),
              details._teamStyleLabels,
              details._teamStyleValues
            );
          });
        }
      });

      list.appendChild(details);
    });

    body.dataset.enhancedProfiles = "true";
    body.classList.remove("p-0");
    body.innerHTML = "";
    body.appendChild(list);
  }

  function getTeamStyleGuideCopy() {
    if (isSwedish()) {
      return {
        eyebrow: "TEAMSTILAR",
        title: "Förstå teamstilarna",
        intro: "Varje teamstil kan bidra med något värdefullt och samtidigt innebära möjliga begränsningar när preferensen blir stark eller situationen kräver något annat.",
        contribution: "Kan bidra med",
        watch: "Var uppmärksam på",
        styles: [
          {
            key: "Connector",
            quadrant: "Utforska",
            contribution: "Ett brett nätverk, nya kontakter och förmåga att koppla samman människor och information.",
            watch: "Att mycket tid läggs på interaktion eller att fler personer involveras än situationen kräver."
          },
          {
            key: "Catalyst",
            quadrant: "Utforska",
            contribution: "Nya idéer, alternativa perspektiv och vilja att utmana status quo för att hitta nya vägar framåt.",
            watch: "Förändring för förändringens skull eller lösningar som blir mer komplexa än de behöver vara."
          },
          {
            key: "Director",
            quadrant: "Leda",
            contribution: "Tydlighet kring riktning, roller och beslut samt trygghet i att koordinera och påverka teamet.",
            watch: "Att bli alltför styrande eller gå för snabbt till beslut utan att fånga upp andras perspektiv."
          },
          {
            key: "Energiser",
            quadrant: "Leda",
            contribution: "Energi, tempo och optimism som kan hjälpa teamet genom utmaningar och få saker att hända.",
            watch: "För många samtidiga initiativ, snabba riktningsbyten eller ett tempo som inte fungerar för alla."
          },
          {
            key: "Architect",
            quadrant: "Leverera",
            contribution: "Struktur, planering och förmåga att omsätta idéer till konkreta aktiviteter, resurser och genomförbara planer.",
            watch: "Överplanering som försenar genomförandet eller svårighet att ändra planen när förutsättningarna förändras."
          },
          {
            key: "Harmoniser",
            quadrant: "Leverera",
            contribution: "Stöd, omtanke och uppmärksamhet på andras behov som kan stärka sammanhållning och samarbete.",
            watch: "Att bli alltför angelägen om att tillgodose andra, få svårt att sätta gränser eller bli för beroende av gemensamma arbetssätt."
          },
          {
            key: "Analyst",
            quadrant: "Kritiskt granska",
            contribution: "Objektivitet och analytiskt tänkande som hjälper teamet att pröva alternativ och fatta genomtänkta beslut.",
            watch: "Att analysen tar så mycket plats att handling fördröjs eller att nya idéer möts med mer kritik än situationen behöver."
          },
          {
            key: "Auditor",
            quadrant: "Kritiskt granska",
            contribution: "Kvalitetsmedvetenhet, detaljfokus och uthållighet i att säkerställa att löften och åtaganden faktiskt håller.",
            watch: "Att för mycket tid läggs på detaljer med lågt värde eller att regler och planer följs för strikt när omständigheterna har ändrats."
          }
        ]
      };
    }

    return {
      eyebrow: "TEAM STYLES",
      title: "Understand the team styles",
      intro: "Each team style can make a valuable contribution while also creating possible limitations when the preference becomes strong or the situation calls for something different.",
      contribution: "Can contribute",
      watch: "Watch for",
      styles: [
        {
          key: "Connector",
          quadrant: "Exploring",
          contribution: "A broad network, new connections and the ability to link people with useful information and support.",
          watch: "Spending too much time interacting or involving more people than the situation requires."
        },
        {
          key: "Catalyst",
          quadrant: "Exploring",
          contribution: "New ideas, alternative perspectives and a willingness to challenge the status quo to find new ways forward.",
          watch: "Change for its own sake or solutions that become more complex than they need to be."
        },
        {
          key: "Director",
          quadrant: "Directing",
          contribution: "Clarity about direction, roles and decisions, with confidence in coordinating and influencing the team.",
          watch: "Becoming overly directive or moving to decisions too quickly without hearing other perspectives."
        },
        {
          key: "Energiser",
          quadrant: "Directing",
          contribution: "Energy, pace and optimism that can help the team through challenges and keep action moving.",
          watch: "Too many simultaneous initiatives, rapid changes of direction or a pace that does not work for everyone."
        },
        {
          key: "Architect",
          quadrant: "Delivering",
          contribution: "Structure, planning and the ability to turn ideas into concrete activities, resources and workable plans.",
          watch: "Over-planning that delays action or difficulty adapting the plan when circumstances change."
        },
        {
          key: "Harmoniser",
          quadrant: "Delivering",
          contribution: "Support, consideration and attention to other people's needs, strengthening cohesion and collaboration.",
          watch: "Trying too hard to please others, struggling to set boundaries or relying too heavily on team-based ways of working."
        },
        {
          key: "Analyst",
          quadrant: "Critiquing",
          contribution: "Objectivity and analytical thinking that help the team test alternatives and make well-considered decisions.",
          watch: "Analysis taking so much space that action is delayed or new ideas receive more criticism than the situation needs."
        },
        {
          key: "Auditor",
          quadrant: "Critiquing",
          contribution: "Quality awareness, attention to detail and persistence in making sure promises and commitments hold up.",
          watch: "Spending too much time on low-value details or following rules and plans too rigidly when circumstances have changed."
        }
      ]
    };
  }

  function initTeamStyleGuide() {
    const chartElement = document.getElementById("teamStyleAverageChart");
    const page = chartElement && chartElement.closest(".talena-team-page");

    if (!chartElement || !page || document.querySelector(".team-style-guide-card")) {
      return;
    }

    const addCandidatesAction = page.querySelector(
      "a.team-primary-action[href*='/members/']"
    );
    const candidatesCard = addCandidatesAction && addCandidatesAction.closest(".card");

    if (!candidatesCard) {
      return;
    }

    const labels = getTeamStyleLabelMap(chartElement);
    const copy = getTeamStyleGuideCopy();

    const cards = copy.styles.map(function (style) {
      const label = labels[style.key] || style.key;
      return `
        <details class="team-style-guide-item">
          <summary>
            <div>
              <div class="team-style-guide-quadrant">${escapeHtml(style.quadrant)}</div>
              <div class="team-style-guide-name">${escapeHtml(label)}</div>
            </div>
            <span class="team-guide-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div class="team-style-guide-body">
            <div class="team-style-guide-copy team-style-guide-copy-positive">
              <div class="team-style-guide-copy-label">${escapeHtml(copy.contribution)}</div>
              <p>${escapeHtml(style.contribution)}</p>
            </div>
            <div class="team-style-guide-copy team-style-guide-copy-watch">
              <div class="team-style-guide-copy-label">${escapeHtml(copy.watch)}</div>
              <p>${escapeHtml(style.watch)}</p>
            </div>
          </div>
        </details>
      `;
    }).join("");

    const wrapper = document.createElement("div");
    wrapper.className = "card mb-4 team-style-guide-card";
    wrapper.innerHTML = `
      <div class="card-header team-style-guide-header">
        <div>
          <div class="team-guide-eyebrow"><span></span>${escapeHtml(copy.eyebrow)}</div>
          <h2 class="team-section-title">${escapeHtml(copy.title)}</h2>
          <p class="team-section-copy">${escapeHtml(copy.intro)}</p>
        </div>
      </div>
      <div class="card-body">
        <div class="team-style-guide-grid">${cards}</div>
      </div>
    `;

    candidatesCard.parentNode.insertBefore(wrapper, candidatesCard);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCandidateSearch();
    initTeamStyleRankBars();
    initTeamStyleChart();
    initTeamModelGuide();
    initTeamMemberProfiles();
    initTeamStyleGuide();
  });
})();