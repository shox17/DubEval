// Comparison screen: the recommended dub and why, the ranking, every check side by side, then one tab per dub with
// its own review (synced players and timeline). Decisions and levels come from the server; nothing is ranked here.
import { api, fill, h, noteUsageStep, setAddress, state, t } from "./app.js";
import { renderReview } from "./review.js";
import { exportButton } from "./export.js";

function badge(comp, level, text) {
  return h("span", { class: `badge ${level}` }, text || comp.badges[level] || level);
}

function recommendation(comp, jobId) {
  const r = comp.recommendation, why = comp.reasoning, lb = comp.labels;
  return h("section", { class: `verdict card ${r.verdict}` },
    h("div", { class: "row" }, h("h1", {}, lb.title), h("span", { class: "grow" }),
      h("div", { class: "head-actions" },
        r.ready ? null : h("span", { class: "badge check" }, r.status_label),      // first place, not a recommendation
        badge(comp, r.verdict, r.verdict_label),
        h("a", { class: "button", href: "#/new" }, t("w.review.new")), exportButton(jobId))),
    h("p", { class: "headline big" }, r.headline),
    r.caution ? h("p", { class: "caution", role: "note" }, r.caution) : null,
    r.warning ? h("p", { class: "error" }, r.warning) : null,
    r.fix_first.length ? [h("h3", {}, lb.fix_first), h("ul", {}, r.fix_first.map(x => h("li", {}, x)))] : null,
    h("h3", {}, lb["sec.reasoning"]),
    h("ul", { class: "reasons" }, why.summary.map(x => h("li", {}, x))),
    h("details", { class: "more" }, h("summary", {}, lb.rule_label + ": " + why.rule_label),
      h("p", { class: "small" }, why.rules_order),
      why.skipped_rules.length ? h("p", { class: "small muted" }, `${lb.skipped}: ${why.skipped_rules.join(", ")}`) : null,
      h("p", { class: "small muted" }, why.translation_note)));
}

function ranking(comp, open) {
  const lb = comp.labels;
  return h("section", { class: "card" }, h("h2", {}, lb.ranking_label),
    h("table", { class: "ranking" },
      h("thead", {}, h("tr", {}, h("th", {}, "#"), h("th", {}, t("w.cmp.dub")), h("th", {}, lb.verdict),
        h("th", { class: "num" }, comp.badges.poor), h("th", { class: "num" }, comp.badges.check),
        h("th", {}, t("w.cmp.problems")))),
      h("tbody", {}, comp.ranking.map(r => h("tr", { class: comp.recommendation.ready && r.dub === comp.recommendation.dub ? "winner" : "" },
        h("td", {}, String(r.rank)),
        h("td", {}, h("button", { type: "button", class: "link", onclick: () => open(r.dub) }, lb[`dub_${r.dub}`])),
        h("td", {}, badge(comp, r.verdict, r.verdict_label)),
        h("td", { class: "num" }, String(r.poor)), h("td", { class: "num" }, String(r.check)),
        h("td", { class: "muted" }, lb[`count_${r.dub}`]))))));
}

function sideBySide(comp) {
  const lb = comp.labels;
  return h("details", { class: "card table-card" }, h("summary", {}, h("strong", {}, lb["sec.table"])),
    h("div", { class: "scroll" }, h("table", { class: "checks" },
      h("thead", {}, h("tr", {}, h("th", {}, lb["table.check"]), comp.dubs.map(d => h("th", {}, lb[`dub_${d}`])))),
      h("tbody", {}, comp.table.map(row => h("tr", {}, h("td", {}, row.label),
        comp.dubs.map(d => h("td", {}, row[d] ? [badge(comp, row[d].level, row[d].badge), " ",
          h("span", { class: "muted small" }, row[d].display ?? "")] : "–"))))))),
    comp.notes.length ? [h("h3", {}, lb["sec.notes"]), h("ul", { class: "small muted" }, comp.notes.map(n => h("li", {}, n)))]
      : null);
}

// The open dub's name; a click turns it into a field (Enter or leaving it saves, Escape cancels, empty takes it away).
function dubName(comp, jobId, dub, saved) {
  const shown = comp.names[dub];
  const text = h("span", { class: `editable dub-name-value${shown ? "" : " empty"}`, tabindex: "0", title: t("w.cmp.name_hint") },
    shown || t("w.cmp.name_add"));
  const edit = () => {
    const given = comp.given_names[dub] || "";
    const field = h("input", { type: "text", class: "dub-name-input", value: given, maxlength: "60", placeholder: shown || "",
      "aria-label": t("w.cmp.name", { d: dub }) });
    let done = false;
    const finish = async save => {
      if (done) return;
      done = true;
      const value = field.value.trim();
      if (save && value !== given) {
        let stored = false;
        try {
          await api(`/api/jobs/${jobId}/dub-name?dub=${dub}`, { method: "PUT", body: JSON.stringify({ name: value }) });
          stored = true;
          await saved();
          return;
        } catch (e) {
          if (stored) text.textContent = value || t("w.cmp.name_add");   // saved; only the rest of the screen is behind
          else alert(e.message);
        }
      }
      field.replaceWith(text);
      text.focus();
    };
    field.addEventListener("keydown", e => {
      if (e.key === "Enter") finish(true);
      if (e.key === "Escape") finish(false);
      e.stopPropagation();                          // not the player's keys while typing
    });
    field.addEventListener("blur", () => finish(true));
    text.replaceWith(field);
    field.focus();
    field.select();
  };
  text.addEventListener("click", edit);
  text.addEventListener("keydown", e => { if (e.key === "Enter") edit(); });
  return h("p", { class: "dub-name small" }, h("span", { class: "muted" }, t("w.cmp.name", { d: dub })), " ", text);
}

export function renderCompare(root, jobId, firstDub) {
  let alive = true, cleanupReview = null;
  root.append(h("p", { class: "muted" }, t("w.review.loading")));
  const load = () => api(`/api/jobs/${jobId}/comparison?lang=${state.lang}`);

  load().then(comp => {
    if (!alive) return;
    noteUsageStep("result_opened", "compare");
    const tabs = h("div", { class: "tabs", role: "tablist", "aria-label": t("w.cmp.dubs") });
    const nameRow = h("div");
    const panel = h("div", { class: "tab-panel", role: "tabpanel" });
    let current = null, cards = [];

    // Everything that shows the dubs' names; the open dub's review (and its players) stays as it is.
    function paint() {
      const fresh = [recommendation(comp, jobId), ranking(comp, open), sideBySide(comp)];
      const wasOpen = !!cards[2]?.open;              // the side-by-side table stays open and scrolled as it was
      const left = wasOpen ? cards[2].querySelector(".scroll").scrollLeft : 0;
      fresh[2].open = wasOpen;
      cards.forEach((c, i) => c.replaceWith(fresh[i]));
      if (wasOpen) fresh[2].querySelector(".scroll").scrollLeft = left;
      cards = fresh;
      const verdictOf = Object.fromEntries(comp.ranking.map(r => [r.dub, r]));
      tabs.replaceChildren(...comp.dubs.map(d => {
        const r = verdictOf[d];
        return h("button", { type: "button", role: "tab", "data-dub": d, onclick: () => open(d) },
          comp.labels[`dub_${d}`], " ", badge(comp, r.verdict, r.verdict_label),
          d === comp.recommendation.dub ? h("span", { class: "star", title: comp.recommendation.status_label },
            comp.recommendation.ready ? "★" : "☆") : null);
      }));
      if (current) showTab();
    }

    function showTab() {
      tabs.querySelectorAll("button").forEach(b => {
        const on = b.dataset.dub === current;
        b.classList.toggle("on", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
      nameRow.replaceChildren(dubName(comp, jobId, current, async () => {
        const next = await load();
        if (!alive) return;
        comp = next;
        paint();
      }));
    }

    function open(dub, scroll = true) {
      if (cleanupReview) cleanupReview();
      current = dub;
      showTab();
      panel.replaceChildren();
      cleanupReview = renderReview(panel, jobId, dub, true);
      setAddress(`#/compare/${jobId}/${dub}`);       // the dialogs over this screen come back to this tab
      if (scroll) tabs.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    cards = [h("div"), h("div"), h("div")];
    fill(root, ...cards, h("h2", { class: "tabs-title" }, t("w.cmp.review_each")), tabs, nameRow, panel);
    paint();
    open(comp.dubs.includes(firstDub) ? firstDub : comp.recommendation.dub, false);
  }).catch(e => {
    if (alive) fill(root, h("p", { class: "error" }, e.message), h("a", { class: "button", href: "#/" }, t("w.progress.back")));
  });

  return () => { alive = false; if (cleanupReview) cleanupReview(); };
}
