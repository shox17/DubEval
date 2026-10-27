// Comparison screen: the recommended dub and why, the ranking, every check side by side, then one tab per dub with
// its own review (synced players and timeline). Decisions and levels come from the server; nothing is ranked here.
import { api, fill, h, state, t } from "./app.js";
import { renderReview } from "./review.js";
import { exportButton } from "./export.js";

function badge(comp, level, text) {
  return h("span", { class: `badge ${level}` }, text || comp.badges[level] || level);
}

function recommendation(comp, jobId) {
  const r = comp.recommendation, why = comp.reasoning, lb = comp.labels;
  return h("section", { class: `verdict card ${r.verdict}` },
    h("div", { class: "row" }, h("h1", {}, lb.title), h("span", { class: "grow" }),
      h("div", { class: "head-actions" }, badge(comp, r.verdict, r.verdict_label),
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
      h("tbody", {}, comp.ranking.map(r => h("tr", { class: r.dub === comp.recommendation.dub ? "winner" : "" },
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

export function renderCompare(root, jobId, firstDub) {
  let alive = true, cleanupReview = null;
  root.append(h("p", { class: "muted" }, t("w.review.loading")));

  api(`/api/jobs/${jobId}/comparison?lang=${state.lang}`).then(comp => {
    if (!alive) return;
    const tabs = h("div", { class: "tabs", role: "tablist", "aria-label": t("w.cmp.dubs") });
    const panel = h("div", { class: "tab-panel", role: "tabpanel" });
    const verdictOf = Object.fromEntries(comp.ranking.map(r => [r.dub, r]));

    function open(dub, scroll = true) {
      if (cleanupReview) cleanupReview();
      tabs.querySelectorAll("button").forEach(b => {
        const on = b.dataset.dub === dub;
        b.classList.toggle("on", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
      panel.replaceChildren();
      cleanupReview = renderReview(panel, jobId, dub, true);
      history.replaceState(null, "", `#/compare/${jobId}/${dub}`);
      if (scroll) tabs.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    for (const d of comp.dubs) {
      const r = verdictOf[d];
      tabs.append(h("button", { type: "button", role: "tab", "data-dub": d, onclick: () => open(d) },
        comp.labels[`dub_${d}`], " ", badge(comp, r.verdict, r.verdict_label),
        d === comp.recommendation.dub ? h("span", { class: "star", title: t("w.cmp.recommended") }, "★") : null));
    }
    fill(root, recommendation(comp, jobId), ranking(comp, open), sideBySide(comp),
      h("h2", { class: "tabs-title" }, t("w.cmp.review_each")), tabs, panel);
    open(comp.dubs.includes(firstDub) ? firstDub : comp.recommendation.dub, false);
  }).catch(e => {
    if (alive) fill(root, h("p", { class: "error" }, e.message), h("a", { class: "button", href: "#/" }, t("w.progress.back")));
  });

  return () => { alive = false; if (cleanupReview) cleanupReview(); };
}
