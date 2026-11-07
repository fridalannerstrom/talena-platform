/* #430: compact, read-only Chefsrapport activity for customers and Talena admins. */
(() => {
  "use strict";
  if (window.TalenaManagerReportActivity) return;

  const isSwedish = () => (document.documentElement.lang || "").startsWith("sv");
  const labels = () => isSwedish() ? ({
    title: "Rapportaktivitet", history: "Visa historik", noEvents: "Ingen rapportaktivitet ännu.",
    edited: "Senast redigerad", exported: "Senast genererad PDF",
    prepared: "PDF förberedd", generated: "PDF genererad",
    saved: "Text redigerad", restored: "AI-text återställd",
    loading: "Hämtar rapporthistorik…", error: "Kunde inte hämta rapporthistorik.",
    previous: "Tidigare redigeringar och exporter", block: "Block", version: "version"
  }) : ({
    title: "Report activity", history: "View history", noEvents: "No report activity yet.",
    edited: "Last edited", exported: "Last PDF generated",
    prepared: "PDF prepared", generated: "PDF generated",
    saved: "Text edited", restored: "AI text restored",
    loading: "Loading report activity…", error: "Could not load report activity.",
    previous: "Previous edits and exports", block: "Block", version: "version"
  });

  const fmt = value => {
    const date = new Date(value);
    if (!value || !Number.isFinite(date.getTime())) return "";
    return new Intl.DateTimeFormat(isSwedish() ? "sv-SE" : "en-GB", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm"
    }).format(date);
  };

  const node = (tag, className, content) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (content !== undefined) el.textContent = content;
    return el;
  };

  const getBlockLabel = key => {
    if (!key) return "";
    if (key === "wellbeing_tips") return isSwedish() ? "Tips för trivsel" : "Wellbeing tips";
    const names = {
      leading_and_working_with_others: isSwedish() ? "Ledarskap och samarbete" : "Leadership and teamwork",
      organising_and_thinking_patterns: isSwedish() ? "Organisation och tankemönster" : "Organisation and thinking",
      interaction_and_emotion_management: isSwedish() ? "Samspel och känslor" : "Interaction and emotions"
    };
    const parts = key.split(":");
    if (parts[0] === "personality" && names[parts[1]]) {
      return names[parts[1]] + " · " +
        (parts[2] === "testbild"
          ? (isSwedish() ? "Testbild" : "Assessment")
          : (isSwedish() ? "Kandidaten beskriver" : "Candidate describes"));
    }
    return isSwedish() ? "Rapporttext" : "Report text";
  };

  function mount(container) {
    if (!container || container.dataset.talenaAuditMounted === "true") return;
    const url = container.dataset.managerReportActivityUrl;
    if (!url) return;
    container.dataset.talenaAuditMounted = "true";
    container.classList.add("talena-report-audit");
    const heading = node("p", "talena-report-audit__title", labels().title);
    const summary = node("div", "talena-report-audit__summary");
    const details = node("details", "talena-report-audit__details");
    const trigger = node("summary", "talena-report-audit__trigger", labels().history);
    const list = node("ol", "talena-report-audit__list");
    details.append(trigger, list);
    container.append(heading, summary, details);

    let sequence = 0;
    async function refresh() {
      const id = ++sequence;
      try {
        const response = await fetch(url, {
          credentials: "same-origin",
          headers: {"X-Requested-With": "XMLHttpRequest"}
        });
        if (!response.ok) throw Error("Report history unavailable");
        const data = await response.json();
        if (id !== sequence || !container.isConnected) return;
        if (!data.ok || !Array.isArray(data.events)) throw Error("Invalid report history");
        summary.replaceChildren();
        for (const [entry, label] of [
          [data.last_edited, labels().edited],
          [data.last_export, labels().exported],
          [!data.last_export ? data.last_prepared : null, labels().prepared]
        ]) {
          if (!entry) continue;
          summary.append(node("span", "talena-report-audit__meta",
            label + ": " + entry.actor + " · " + fmt(entry.at)));
        }
        if (!summary.childElementCount) {
          summary.append(node("span", "talena-report-audit__empty",
            data.events.length ? labels().previous : labels().noEvents));
        }
        list.replaceChildren();
        data.events.forEach(row => {
          const label = ({
            edited: labels().saved, restored: labels().restored,
            prepared: labels().prepared, generated: labels().generated
          })[row.type] || labels().title;
          const item = node("li", "talena-report-audit__item");
          item.append(
            node("span", "talena-report-audit__event", label),
            node("span", "talena-report-audit__actor", row.actor),
            node("time", "talena-report-audit__time", fmt(row.at))
          );
          const block = getBlockLabel(row.block);
          if (block) item.append(node("small", "talena-report-audit__block",
            block + (row.version ? " · v" + row.version : "")));
          list.append(item);
        });
        details.hidden = !data.events.length;
      } catch (_error) {
        if (id !== sequence || !container.isConnected) return;
        summary.replaceChildren(node("span", "talena-report-audit__empty", labels().error));
        details.hidden = true;
      }
    }
    document.addEventListener("talena:manager-report-activity-changed", refresh);
    refresh();
    return {refresh};
  }

  window.TalenaManagerReportActivity = Object.freeze({mount});
  const init = () => document.querySelectorAll("[data-manager-report-activity-url]")
    .forEach(mount);
  const attach = () => {
    init();
    if (!window.MutationObserver) return;
    new MutationObserver(records => {
      records.forEach(record => {
        record.addedNodes.forEach(added => {
          if (added.nodeType !== 1) return;
          if (added.matches?.("[data-manager-report-activity-url]")) mount(added);
          added.querySelectorAll?.("[data-manager-report-activity-url]").forEach(mount);
        });
      });
    }).observe(document.body, {childList:true, subtree:true});
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach, {once:true});
  } else {
    attach();
  }
})();
