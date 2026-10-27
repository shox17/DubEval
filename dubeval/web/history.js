// History screen: every past evaluation summarized (totals, week by week, language pairs, most frequent problems,
// the latest runs) and what reviewers said about the problem intervals. Numbers come from the server.
import { api, fill, go, h, t } from "./app.js";

const PERIOD_KEY = "dubeval.history_days";
const LEVELS = ["good", "check", "poor"];

function readPeriod() {
  try { return localStorage.getItem(PERIOD_KEY) || ""; } catch { return ""; }
}

function tiles(s) {
  const v = s.verdicts;
  const tile = (label, value, cls = "") => h("div", { class: `tile ${cls}` }, h("span", { class: "muted small" }, label),
    h("strong", {}, value));
  return [h("div", { class: "tiles" },
    tile(t("h.dubs"), String(s.dubs)), tile(t("h.good_pct"), `${Math.round(s.good_pct)}%`, "good"),
    tile(t("verdict.check"), String(v.check), "check"), tile(t("verdict.poor"), String(v.poor), "poor")),
  h("p", { class: "muted small" }, t("h.totals", { runs: s.runs, dubs: s.dubs, good: v.good, check: v.check,
    poor: v.poor, pct: Math.round(s.good_pct) }))];
}

// Stacked bars, one per week; the bar's height is the number of dubs that week.
function weekly(s) {
  const most = Math.max(1, ...s.weekly.map(w => w.good + w.check + w.poor));
  return h("section", { class: "card" }, h("h2", {}, t("h.weekly_chart")),
    h("div", { class: "legend small muted" }, LEVELS.map(lv => h("span", {}, h("i", { class: `sw ${lv}` }), t(`verdict.${lv}`)))),
    h("div", { class: "bars", role: "img", "aria-label": t("h.weekly_chart") }, s.weekly.map(w => {
      const n = w.good + w.check + w.poor;
      return h("div", { class: "bar-col", title: `${w.week}: ${t("h.week_counts", { n, good: w.good, check: w.check, poor: w.poor })}` },
        h("div", { class: "bar", style: `height:${(n / most) * 100}%` },
          LEVELS.slice().reverse().map(lv => w[lv] ? h("div", { class: `seg ${lv}`, style: `flex:${w[lv]}` }) : null)),
        h("span", { class: "small muted" }, w.week.slice(5)));
    })));
}

function table(headers, rows, numeric = []) {
  return h("div", { class: "scroll" }, h("table", {},
    h("thead", {}, h("tr", {}, headers.map((x, i) => h("th", { class: numeric.includes(i) ? "num" : "" }, x)))),
    h("tbody", {}, rows.map(r => h("tr", {}, r.map((x, i) => h("td", { class: numeric.includes(i) ? "num" : "" }, x)))))));
}

function badge(level) {
  return h("span", { class: `badge ${level}` }, t(`verdict.${level}`));
}

function pairs(s) {
  return h("section", { class: "card" }, h("h2", {}, t("h.pairs")),
    table([t("h.pair"), t("h.dubs"), ...LEVELS.map(lv => t(`verdict.${lv}`)), t("h.timing"), t("h.meaning")],
      s.pairs.map(p => [p.languages, p.dubs, p.good, p.check, p.poor,
        p.overlap_pct === null ? "–" : `${Math.round(p.overlap_pct)}%`,
        p.meaning_score === null ? "–" : `${p.meaning_score.toFixed(1)} / 10`]), [1, 2, 3, 4, 5, 6]));
}

function problems(s) {
  return h("section", { class: "card" }, h("h2", {}, t("h.problems")),
    s.problems.length
      ? table([t("table.measure"), t("verdict.poor"), t("verdict.check")],
        s.problems.slice(0, 15).map(x => [t(`r.m.${x.measure}`), x.poor, x.check]), [1, 2])
      : h("p", { class: "muted" }, t("h.no_problems")));
}

function reviewers(fb) {
  return h("section", { class: "card" }, h("h2", {}, t("f.title")),
    fb.intervals
      ? [h("p", { class: "muted small" }, t("f.totals", { n: fb.intervals, real: fb.real, false: fb.false_alarm,
        pct: Math.round(fb.confirmed_pct) })),
        table([t("f.check"), t("f.real"), t("f.false"), t("f.confirmed"), ""],
          fb.checks.map(c => [t(`r.m.${c.check}`), c.real, c.false_alarm, `${Math.round(c.confirmed_pct)}%`,
            h("span", { class: `status ${c.status}` }, t(`f.status.${c.status}`))]), [1, 2, 3])]
      : h("p", { class: "muted" }, t("w.hist.no_votes")));
}

// Opens a past evaluation in the app's own review (or its comparison, on that dub's tab), not as a file.
async function openPast(report, link) {
  link.setAttribute("aria-busy", "true");
  try {
    const past = await api(`/api/history/open?path=${encodeURIComponent(report)}`, { method: "POST" });
    go(past.kind === "comparison" ? `#/compare/${past.id}/${past.dub || "A"}` : `#/report/${past.id}`);
  } catch (e) {
    link.removeAttribute("aria-busy");
    alert(e.message);
  }
}

function recent(s) {
  return h("section", { class: "card" }, h("h2", {}, t("h.recent")),
    table([t("h.when"), t("w.hist.verdict"), t("w.hist.title"), t("h.pair")],
      s.recent.map(r => [h("span", { class: "mono" }, r.time.slice(0, 16)), badge(r.verdict),
        r.report ? h("a", { href: "#", onclick: e => { e.preventDefault(); openPast(r.report, e.currentTarget); } },
          r.title || "–") : (r.title || "–"),
        r.languages])));
}

export function renderHistory(root) {
  let alive = true;
  const periods = [["", t("h.all_time")], ["7", t("h.last_days", { n: 7 })], ["30", t("h.last_days", { n: 30 })],
    ["90", t("h.last_days", { n: 90 })]];
  const period = h("select", { id: "period" }, periods.map(([v, label]) => h("option", { value: v, selected: v === readPeriod() }, label)));
  const body = h("div", {}, h("p", { class: "muted" }, t("w.loading")));

  async function load() {
    try {
      const data = await api(`/api/history${period.value ? `?days=${period.value}` : ""}`);
      if (!alive) return;
      const s = data.history;
      if (!s.dubs) { fill(body, h("p", { class: "muted card" }, t("h.empty")), reviewers(data.feedback)); return; }
      fill(body, tiles(s), weekly(s), h("div", { class: "split" }, pairs(s), problems(s)), reviewers(data.feedback),
        recent(s));
    } catch (e) {
      if (alive) fill(body, h("p", { class: "error" }, e.message));
    }
  }
  period.addEventListener("change", () => {
    try { localStorage.setItem(PERIOD_KEY, period.value); } catch { /* not kept */ }
    load();
  });
  root.append(h("div", { class: "row" }, h("h1", {}, t("h.title")), h("span", { class: "grow" }),
    h("label", { class: "row" }, h("span", { class: "muted small" }, t("h.days")), period)), body);
  load();
  return () => { alive = false; };
}
