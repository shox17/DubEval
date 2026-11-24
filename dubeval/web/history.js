// History screen: every past evaluation summarized (totals, week by week, language pairs, most frequent problems,
// the latest runs) and what reviewers said about the problem intervals. Numbers come from the server.
import { api, fill, go, h, state, t } from "./app.js";

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
    tile(t("h.dubs"), String(s.dubs)), tile(t("verdict.good"), String(v.good), "good"),
    tile(t("verdict.check"), String(v.check), "check"), tile(t("verdict.poor"), String(v.poor), "poor")),
  h("p", { class: "muted small" }, t("h.totals", { runs: s.runs, dubs: s.dubs, good: v.good, check: v.check,
    poor: v.poor, pct: Math.round(s.good_pct) }))];
}

// Stacked bars, one per week; the bar's height is the number of dubs that week, printed over it. A quiet week keeps
// a bar tall enough to see (a week with 2 dubs next to one with 80 was a hairline).
// A week by its first day, named in the page's language ("Nov 16"): "11-16" read as a range or a code.
function weekName(iso) {
  try {
    return new Intl.DateTimeFormat(state.lang, { month: "short", day: "numeric" }).format(new Date(`${iso}T00:00:00`));
  } catch { return iso.slice(5); }
}

function weekly(s) {
  const most = Math.max(1, ...s.weekly.map(w => w.good + w.check + w.poor));
  return h("section", { class: "card" }, h("h2", {}, t("h.weekly_chart")),
    h("div", { class: "legend small muted" }, LEVELS.map(lv => h("span", {}, h("i", { class: `sw ${lv}` }), t(`verdict.${lv}`)))),
    h("div", { class: "bars", role: "img", "aria-label": t("h.weekly_chart") }, s.weekly.map(w => {
      const n = w.good + w.check + w.poor;
      return h("div", { class: "bar-col", title: `${w.week}: ${t("h.week_counts", { n, good: w.good, check: w.check, poor: w.poor })}` },
        n ? h("span", { class: "bar-n" }, String(n)) : null,
        h("div", { class: "bar", style: `height:${n ? `max(10px, ${(n / most) * 80}%)` : "0"}` },
          LEVELS.slice().reverse().map(lv => w[lv] ? h("div", { class: `seg ${lv}`, style: `flex:${w[lv]}` }) : null)),
        h("span", { class: "small muted" }, weekName(w.week)));
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

// A language pair in the page's language ("en→es" → "영어 → 스페인어"); records keep the names they were made with.
function pairName(codes, fallback) {
  const [a, b] = (codes || "").split("→");
  if (!a || !b || a === "?" || b === "?") return fallback || "–";
  try {
    const names = new Intl.DisplayNames([state.lang], { type: "language" });
    const cap = x => x.charAt(0).toLocaleUpperCase(state.lang) + x.slice(1);
    return `${cap(names.of(a))} → ${cap(names.of(b))}`;
  } catch { return fallback || "–"; }
}

function pairs(s) {
  return h("section", { class: "card" }, h("h2", {}, t("h.pairs")),
    table([t("h.pair"), t("h.dubs"), ...LEVELS.map(lv => t(`verdict.${lv}`)), t("h.score_avg"), t("h.timing"), t("h.meaning")],
      s.pairs.map(p => [pairName(p.pair, p.languages), p.dubs, p.good, p.check, p.poor,
        p.score == null ? "–" : String(Math.round(p.score)),
        p.overlap_pct === null ? "–" : `${Math.round(p.overlap_pct)}%`,
        p.meaning_score === null ? "–" : `${p.meaning_score.toFixed(1)} / 10`]), [1, 2, 3, 4, 5, 6, 7]));
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
async function openPast(row, link) {
  link.setAttribute("aria-busy", "true");
  try {
    const past = await api(`/api/evaluations/${row.run}/open`, { method: "POST" });
    go(past.kind === "comparison" ? `#/compare/${past.id}/${row.dub || "A"}` : `#/report/${past.id}`);
  } catch (e) {
    link.removeAttribute("aria-busy");
    alert(e.message);
  }
}

function recent(s) {
  return h("section", { class: "card" }, h("h2", {}, t("h.recent")),
    table([t("h.when"), t("w.hist.verdict"), t("h.score"), t("w.hist.title"), t("h.pair")],
      s.recent.map(r => [h("span", { class: "mono" }, r.time.slice(0, 16)), badge(r.verdict),
        r.score == null ? "–" : t(r.score_provisional ? "w.home.score_provisional" : "w.home.score", { score: r.score }),
        [h("a", { href: "#", onclick: e => { e.preventDefault(); openPast(r, e.currentTarget); } }, r.title || "–"),
        // a dub's own name only when it says something the title doesn't
        r.dub ? h("span", { class: "hist-dub small" },
          t("w.start.dub_n", { d: r.dub }) + (r.dub_name && r.dub_name !== r.title ? ` · ${r.dub_name}` : "")) : null],
        pairName(r.language_pair, r.languages)]), [2]),
    // a dash where every card shows a score: say why, and where the score is
    s.recent.some(r => r.score == null) ? h("p", { class: "muted small" }, t("w.hist.no_score")) : null);
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
      // nothing evaluated: no votes either, so no empty feedback table under it
      if (!s.dubs) { fill(body, h("p", { class: "muted card" }, t("h.empty"))); return; }
      fill(body, tiles(s), weekly(s), h("div", { class: "split hist-split" }, pairs(s), problems(s)), reviewers(data.feedback),
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
