// Review screen: both videos in sync, a timeline (waveforms, lines, problem intervals), the selected item's details,
// and every measure of the report. Levels and texts come from the server's report; nothing is graded here.
import { api, fill, fmtTime, h, state, t } from "./app.js";
import { exportButton } from "./export.js";

const GUTTER = 96;                                  // px for the lane names on the left of the timeline
const LANES = [["ruler", 22], ["original", 52], ["dub", 52], ["lines", 30], ["issues", 34]];
const LINE_CATEGORIES = ["line_length", "line_overrun"];

const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const overlaps = (a, b) => a.start < b.end && b.start < a.end;
const texts = (segments, indexes) => (indexes || []).map(i => segments[i]?.text?.trim()).filter(Boolean).join(" ");

function badge(rep, level) {
  return h("span", { class: `badge ${level}` }, rep.badges[level] || level);
}

// Original time → dub time: by part when the dub is cut differently, else by the one shift; null where the dub
// has nothing (a part it lacks).
function dubTime(data, sec) {
  if (data.parts) {
    const p = data.parts.find(p => sec >= p.start && sec < p.end);
    return p ? sec + p.offset_sec : null;
  }
  return sec + (data.offset_sec || 0);
}

// Dub time → original time (the other way round); null where the original has nothing at that moment of the dub.
function originalTime(data, sec) {
  if (data.parts) {
    const p = data.parts.find(p => sec >= p.start + p.offset_sec && sec < p.end + p.offset_sec);
    return p ? sec - p.offset_sec : null;
  }
  return sec - (data.offset_sec || 0);
}

// The two players. Only the one chosen under "Listen to" plays, with its sound; the other stands still. Choosing it
// moves it to the moment the first one reached and plays it from there (if the first was playing). Times given out and taken in are on the
// original's timeline, which the timeline draws.
function players(data, jobId, q, onTime) {
  const original = h("video", { src: `/api/jobs/${jobId}/media/original${q}`, preload: "auto", playsinline: true });
  const dub = h("video", { src: `/api/jobs/${jobId}/media/dub${q}`, preload: "auto", playsinline: true });
  let listen = "dub", raf = null, now = 0;
  const active = () => (listen === "original" ? original : dub);
  const other = () => (listen === "original" ? dub : original);
  const apply = () => { original.muted = listen !== "original"; dub.muted = listen !== "dub"; };
  apply();

  function follow() {
    const from = active(), to = other();
    const sec = listen === "original" ? from.currentTime : originalTime(data, from.currentTime);
    if (sec !== null && sec >= 0) now = sec;
    if (!to.paused) to.pause();                     // the other one stands still until it is chosen
    onTime(now, !from.paused);
  }
  function loop() { follow(); raf = requestAnimationFrame(loop); }
  loop();

  function place(sec) {
    now = Math.max(0, sec);
    original.currentTime = now;
    const m = dubTime(data, now);
    if (m !== null && m >= 0) dub.currentTime = m;
  }

  const ctl = {
    original, dub,
    get time() { return now; },
    get playing() { return !active().paused; },
    seek(sec) { place(sec); follow(); },
    toggle() { const v = active(); v.paused ? v.play().catch(() => {}) : v.pause(); },
    setListen(side) {
      if (side === listen) return;
      const wasPlaying = !active().paused;
      active().pause();
      listen = side;
      apply();
      place(now);                                   // the chosen one carries on from the same moment
      if (wasPlaying) active().play().catch(() => {});
    },
    stop() { cancelAnimationFrame(raf); original.pause(); dub.pause(); },
  };
  return ctl;
}

// The reviewer's votes on the problem intervals (index → "real" | "false_alarm"), cast on a problem's card.
function voteStore(data, jobId, q) {
  const votes = { ...(data.votes || {}) }, listeners = [];
  return {
    get: i => votes[String(i)],
    async set(i, vote) {
      await api(`/api/jobs/${jobId}/votes${q}`, { method: "POST", body: JSON.stringify({ index: i, vote }) });
      votes[String(i)] = vote;
      listeners.forEach(f => f(i, vote));
    },
    onChange: f => listeners.push(f),
  };
}

// Problem intervals stacked into rows so overlapping ones stay visible.
function stack(intervals) {
  const rowsEnd = [];
  return intervals.map(iv => {
    let row = rowsEnd.findIndex(end => end <= iv.start);
    if (row < 0) { row = rowsEnd.length; rowsEnd.push(0); }
    rowsEnd[row] = iv.end;
    return row;
  });
}

function timeline(data, onSeek, onSelect) {
  const rep = data.report, duration = data.duration_sec || 1;
  const canvas = h("canvas", { class: "timeline", tabindex: "0", "aria-label": t("w.tl.label") });
  // Zoomed in, a scrollbar under the lanes moves along the video (dragging the timeline does too).
  const track = h("div", { class: "tl-scroll-track" });
  const scroller = h("div", { class: "tl-scroll", hidden: true }, track);
  const wrap = h("div", { class: "timeline-wrap" }, canvas, scroller);
  let syncing = false;
  const height = LANES.reduce((s, [, px]) => s + px, 0);
  const top = {};
  LANES.reduce((y, [id, px]) => { top[id] = [y, px]; return y + px; }, 0);
  const intervals = rep.problem_intervals.map((iv, i) => ({ ...iv, index: i }));
  const rows = stack(intervals), nRows = Math.max(1, ...rows.map(r => r + 1));
  const flagged = data.lines.map(line => {
    const hits = intervals.filter(iv => LINE_CATEGORIES.includes(iv.category) && overlaps(iv, line));
    return hits.some(iv => iv.severity === "poor") ? "poor" : hits.length ? "check" : null;
  });
  const view = { start: 0, pps: 1 }, peaks = { original: null, dub: null };
  let width = 0, playhead = 0, selected = null, fitted = false;
  let autoFit = true;                               // the whole video fills the width until the person zooms

  const x = sec => GUTTER + (sec - view.start) * view.pps;
  const sec = px => view.start + (px - GUTTER) / view.pps;
  const clampView = () => {
    const visible = (width - GUTTER) / view.pps;
    view.start = Math.min(Math.max(0, view.start), Math.max(0, duration - visible));
  };

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    width = canvas.clientWidth;
    if ((!fitted || autoFit) && width > GUTTER) { view.pps = (width - GUTTER) / duration; fitted = true; }
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.height = `${height}px`;
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const c = { bg: css("--panel"), line: css("--line"), text: css("--muted"), strong: css("--text"),
      original: css("--wave-original"), dub: css("--wave-dub"), block: css("--block"), check: css("--check"),
      poor: css("--poor"), accent: css("--accent") };
    g.fillStyle = c.bg;
    g.fillRect(0, 0, width, height);
    g.font = "12px system-ui, sans-serif";
    g.textBaseline = "middle";

    // ruler: a tick step that keeps labels about 80 px apart
    const [ry, rh] = top.ruler, steps = [0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
    const step = steps.find(s => s * view.pps >= 80) || 1200;
    g.fillStyle = c.text;
    for (let s = Math.floor(view.start / step) * step; x(s) < width; s += step) {
      if (x(s) < GUTTER) continue;
      g.fillRect(x(s), ry + rh - 6, 1, 6);
      g.fillText(fmtTime(s).replace(/\.0$/, ""), x(s) + 3, ry + rh / 2 - 2);
    }

    for (const side of ["original", "dub"]) {
      const [y, lh] = top[side], p = peaks[side], mid = y + lh / 2;
      g.fillStyle = c[side];
      if (p) {
        const per = p.per_sec, list = p.peaks;
        for (let px = GUTTER; px < width; px++) {
          const a = Math.floor(sec(px) * per), b = Math.max(a + 1, Math.floor(sec(px + 1) * per));
          let v = 0;
          for (let i = Math.max(0, a); i < Math.min(list.length, b); i++) v = Math.max(v, list[i]);
          const hgt = Math.max(1, v * (lh - 8));
          g.fillRect(px, mid - hgt / 2, 1, hgt);
        }
      } else {
        g.fillRect(GUTTER, mid, width - GUTTER, 1);
      }
    }

    const [ly, lh] = top.lines;
    data.lines.forEach((line, i) => {
      const a = Math.max(GUTTER, x(line.start)), b = x(line.end);
      if (b < GUTTER || a > width) return;
      g.fillStyle = flagged[i] ? c[flagged[i]] : c.block;
      g.globalAlpha = selected?.kind === "line" && selected.i === i ? 1 : 0.75;
      g.fillRect(a, ly + 5, Math.max(2, b - a - 1), lh - 10);
      g.globalAlpha = 1;
      if (b - a > 22) { g.fillStyle = c.strong; g.fillText(String(line.n), a + 4, ly + lh / 2); }
    });

    const [iy, ih] = top.issues, rh2 = (ih - 6) / nRows;
    intervals.forEach((iv, i) => {
      const a = Math.max(GUTTER, x(iv.start)), b = x(iv.end);
      if (b < GUTTER || a > width) return;
      const y = iy + 3 + rows[i] * rh2, w = Math.max(3, b - a), hh = Math.max(3, rh2 - 2);
      g.fillStyle = iv.severity === "poor" ? c.poor : c.check;
      g.globalAlpha = selected?.kind === "issue" && selected.i === iv.index ? 1 : 0.7;
      g.fillRect(a, y, w, hh);
      g.globalAlpha = 1;
    });

    if (selected) {
      const item = selected.kind === "line" ? data.lines[selected.i] : intervals[selected.i];
      g.strokeStyle = c.strong;
      g.lineWidth = 1;
      g.strokeRect(Math.max(GUTTER, x(item.start)) + 0.5, top.original[0] + 0.5,
        Math.max(2, x(item.end) - Math.max(GUTTER, x(item.start))), height - top.original[0] - 1);
    }

    // lane names over a solid gutter
    g.fillStyle = c.bg;
    g.fillRect(0, 0, GUTTER, height);
    g.fillStyle = c.line;
    for (const [id] of LANES.slice(1)) g.fillRect(0, top[id][0], width, 1);
    g.fillRect(GUTTER - 1, 0, 1, height);
    g.fillStyle = c.text;
    for (const [id] of LANES.slice(1)) g.fillText(t(`w.tl.${id}`), 10, top[id][0] + top[id][1] / 2);

    if (x(playhead) >= GUTTER && x(playhead) <= width) {
      g.fillStyle = c.accent;
      g.fillRect(Math.round(x(playhead)), 0, 2, height);
    }
    syncScroller();
  }

  // The scrollbar shows where the view is; it appears only when the whole video doesn't fit.
  function syncScroller() {
    const visible = width - GUTTER, total = duration * view.pps;
    scroller.hidden = total <= visible + 1;
    canvas.classList.toggle("zoomed", !scroller.hidden);
    if (scroller.hidden) return;
    scroller.style.marginLeft = `${GUTTER}px`;
    track.style.width = `${Math.ceil(total)}px`;
    syncing = true;
    scroller.scrollLeft = view.start * view.pps;
    requestAnimationFrame(() => { syncing = false; });
  }
  scroller.addEventListener("scroll", () => {
    if (syncing) return;
    view.start = scroller.scrollLeft / view.pps;
    clampView();
    draw();
  });

  // Dragging the timeline sideways moves the view; a click without a drag still seeks or selects.
  let drag = null, dragged = false;
  canvas.addEventListener("pointerdown", e => {
    if (e.button !== 0 || scroller.hidden) return;
    drag = { x: e.clientX, start: view.start, id: e.pointerId };
    dragged = false;
  });
  canvas.addEventListener("pointermove", e => {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    if (!dragged && Math.abs(dx) < 4) return;
    if (!dragged) { dragged = true; canvas.setPointerCapture(drag.id); canvas.classList.add("dragging"); }
    view.start = drag.start - dx / view.pps;
    clampView();
    draw();
  });
  const endDrag = () => { drag = null; canvas.classList.remove("dragging"); };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);

  function hit(px, py) {
    const s = sec(px), [ly, lh] = top.lines, [iy, ih] = top.issues;
    if (py >= ly && py < ly + lh) {
      const i = data.lines.findIndex(l => s >= l.start && s <= l.end);
      if (i >= 0) return { kind: "line", i };
    }
    if (py >= iy && py < iy + ih) {
      const row = Math.floor((py - iy - 3) / ((ih - 6) / nRows));
      const tol = 4 / view.pps;
      const found = intervals.filter((iv, i) => s >= iv.start - tol && s <= iv.end + tol && (rows[i] === row || nRows === 1));
      const pick = found.sort((a, b) => (a.end - a.start) - (b.end - b.start))[0];
      if (pick) return { kind: "issue", i: pick.index };
    }
    return null;
  }

  canvas.addEventListener("click", e => {
    if (dragged) { dragged = false; return; }       // the end of a drag, not a click
    const r = canvas.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
    if (px < GUTTER) return;
    const found = hit(px, py);
    if (found) {
      const item = found.kind === "line" ? data.lines[found.i] : intervals[found.i];
      onSelect(found);
      onSeek(item.start);
    } else {
      onSeek(sec(px));
    }
  });
  canvas.addEventListener("wheel", e => {
    if (!(e.ctrlKey || e.metaKey) && scroller.hidden) return;   // nothing to move: the page scrolls as usual
    e.preventDefault();
    const r = canvas.getBoundingClientRect(), px = Math.max(GUTTER, e.clientX - r.left);
    if (e.ctrlKey || e.metaKey) {
      const at = sec(px), min = (width - GUTTER) / duration, max = 400;
      view.pps = Math.min(max, Math.max(min, view.pps * Math.exp(-e.deltaY * 0.002)));
      autoFit = false;
      view.start = at - (px - GUTTER) / view.pps;
    } else {
      // A wheel notch moves a tenth of the view (a pixel-precise touchpad moves by its own amount).
      const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      const visible = (width - GUTTER) / view.pps;
      view.start += e.deltaMode === 1 ? Math.sign(delta) * visible / 10 : delta / view.pps;
    }
    clampView();
    draw();
  }, { passive: false });
  new ResizeObserver(() => { clampView(); draw(); }).observe(wrap);

  function zoom(factor) {
    const centre = view.start + (width - GUTTER) / view.pps / 2;
    view.pps = Math.min(400, Math.max((width - GUTTER) / duration, view.pps * factor));
    autoFit = false;
    view.start = centre - (width - GUTTER) / view.pps / 2;
    clampView();
    draw();
  }

  return {
    el: wrap,
    setPeaks(side, p) { peaks[side] = p; draw(); },
    setTime(s, playing) {
      if (Math.abs(s - playhead) < 1e-3) return;
      playhead = s;
      const visible = (width - GUTTER) / view.pps;
      if (playing && (s > view.start + visible * 0.92 || s < view.start)) { view.start = s - visible * 0.1; clampView(); }
      draw();
    },
    select(item) { selected = item; draw(); },
    refresh: () => draw(),
    zoomIn: () => zoom(1.6),
    zoomOut: () => zoom(1 / 1.6),
    fit() { autoFit = true; view.pps = (width - GUTTER) / duration; view.start = 0; draw(); },
    intervals,
  };
}

function detailPanel(data, store) {
  const rep = data.report, el = h("aside", { class: "detail card" });
  const lineTexts = line => [texts(data.original_segments, line.original), texts(data.dub_segments, line.dub)];
  const speechIn = (segments, range) => segments.filter(s => overlaps(s, range)).map(s => s.text.trim()).join(" ");

  // One problem's card: what was found, and the reviewer's verdict on it (saved for History and `dubeval feedback`).
  function issueRow(iv, i) {
    const voteBtn = (v, label) => h("button", { type: "button", class: `vote ${store.get(i) === v ? "on" : ""}`,
      "aria-pressed": store.get(i) === v ? "true" : "false", onclick: async () => {
        try { await store.set(i, v); } catch (e) { alert(e.message); }
      } }, label);
    return h("div", { class: "issue" },
      h("div", { class: "row" }, badge(rep, iv.severity), h("strong", {}, iv.check_label || iv.category_label),
        h("span", { class: "grow" }), h("span", { class: "muted mono" }, `${fmtTime(iv.start)} – ${fmtTime(iv.end)}`)),
      h("p", {}, iv.description),
      h("div", { class: "row votes" }, h("span", { class: "muted small" }, t("w.vote.ask")),
        voteBtn("real", t("w.vote.real")), voteBtn("false_alarm", t("w.vote.false_alarm"))));
  }

  // The translation check's scores for one line (1-10 on five criteria), why the low ones are low, the error type
  // and a suggested translation.
  const CRITERIA = [["semantic_accuracy", "meaning"], ["linguistic_naturalness", "naturalness"],
    ["contextual_consistency", "context_fit"], ["terminology_consistency", "terminology"],
    ["localization_appropriateness", "localization"]];
  function rubricOf(n) {
    const rb = (data.rubric || {})[String(n)];
    if (!rb) return null;
    const meaning = rb.scores.semantic_accuracy;
    const low = CRITERIA.filter(([c]) => rb.scores[c] <= 6);
    const level = rb.misheard ? "info" : meaning <= 4 ? "poor" : low.length ? "check" : "good";
    return h("div", { class: "rubric" },
      h("h3", {}, t("w.detail.translation")),
      h("p", { class: "row" }, badge(rep, level), h("span", {}, t("w.detail.meaning_score", { n: meaning })),
        rb.error_type && level !== "good" ? h("span", { class: "muted" }, `· ${rb.error_type}`) : null),
      rb.misheard ? h("p", { class: "muted small" }, t("w.detail.misheard")) : null,
      low.length ? h("ul", { class: "rubric-low" }, low.map(([c, id]) => h("li", {},
        h("strong", {}, `${t(`r.m.${id}`)} ${rb.scores[c]}/10`), rb.reasons[c] ? ` — ${rb.reasons[c]}` : ""))) :
        h("p", { class: "muted small" }, t("w.detail.all_fine")),
      rb.suggested && level !== "good" ? h("div", { class: "suggested" },
        h("span", { class: "muted small" }, t("w.detail.suggested")), h("p", {}, rb.suggested)) : null);
  }

  let current = null;
  function show(item) {
    current = item;
    if (!item) {
      fill(el, h("p", { class: "muted" }, t("w.detail.empty")));
      return;
    }
    if (item.kind === "line") {
      const line = data.lines[item.i], [o, d] = lineTexts(line);
      const issues = rep.problem_intervals.map((iv, i) => [iv, i]).filter(([iv]) => overlaps(iv, line));
      const diff = line.diff_pct === null ? "" : ` (${line.diff_pct > 0 ? "+" : ""}${line.diff_pct}%)`;
      fill(el,
        h("div", { class: "row" }, h("h2", {}, t("w.detail.line", { n: line.n })), h("span", { class: "grow" }),
          h("span", { class: "muted mono" }, `${fmtTime(line.start)} – ${fmtTime(line.end)}`)),
        h("dl", { class: "texts" }, h("dt", {}, rep.labels.original), h("dd", {}, o || "–"),
          line.original_script ? [h("dt", {}, t("w.detail.original_script")), h("dd", {}, line.original_script)] : null,
          h("dt", {}, rep.labels.dub), h("dd", {}, d || "–"),
          line.dub_script ? [h("dt", {}, t("w.detail.dub_script")), h("dd", {}, line.dub_script)] : null),
        h("dl", { class: "facts" },
          h("dt", {}, t("w.detail.lengths")),
          h("dd", {}, t("w.detail.lengths_value", { original: line.original_sec.toFixed(1), dub: line.dub_sec.toFixed(1) })
            + diff),
          h("dt", {}, t("w.detail.starts")),
          h("dd", {}, Math.abs(line.start_shift_sec) < 0.05 ? t("w.detail.together")
            : t(line.start_shift_sec > 0 ? "w.detail.later" : "w.detail.earlier",
              { n: Math.abs(line.start_shift_sec).toFixed(1) })),
          line.overrun_sec ? [h("dt", {}, t("w.detail.overrun")),
            h("dd", {}, t("w.detail.seconds", { n: line.overrun_sec.toFixed(1) }))] : null),
        rubricOf(line.n),
        issues.length ? h("h3", {}, t("w.detail.issues")) : null,
        ...issues.map(([iv, i]) => issueRow(iv, i)));
    } else {
      const iv = rep.problem_intervals[item.i];
      fill(el, issueRow(iv, item.i),
        h("dl", { class: "texts" }, h("dt", {}, rep.labels.original), h("dd", {}, speechIn(data.original_segments, iv) || "–"),
          h("dt", {}, rep.labels.dub), h("dd", {}, speechIn(data.dub_segments, iv) || "–")));
    }
  }
  show(null);
  store.onChange(() => show(current));
  return { el, show };
}

// The review flow: every flagged moment in time order, one at a time; go(i) shows moment i. Returns null
// when there is nothing to review.
function reviewFlow(rep, go) {
  const n = rep.problem_intervals.length;
  if (!n) return null;
  const el = h("div", { class: "review-flow" });
  let cur = -1;                                      // -1: not started
  const move = i => { cur = i; go(i); render(); };

  function render() {
    if (cur < 0) {
      fill(el, h("div", { class: "row" }, h("strong", {}, t("w.flow.title")), h("span", { class: "grow" }),
        h("span", { class: "muted small" }, t("w.flow.count", { total: n })),
        h("button", { type: "button", class: "primary", onclick: () => move(0) }, t("w.flow.start"))),
        h("p", { class: "muted small" }, t("w.flow.intro")));
      return;
    }
    fill(el, h("div", { class: "row" }, h("strong", {}, t("w.flow.title")),
      h("span", { class: "muted small" }, t("w.flow.position", { n: cur + 1, total: n })),
      h("span", { class: "grow" }),
      h("button", { type: "button", onclick: () => move((cur - 1 + n) % n) }, t("w.flow.prev")),
      h("button", { type: "button", onclick: () => move((cur + 1) % n) }, t("w.flow.next"))),
      h("p", { class: "muted small" }, t("w.flow.keys")));
  }
  render();
  return {
    el,
    get active() { return cur >= 0; },
    next: () => move((cur + 1) % n), prev: () => move((cur - 1 + n) % n),
  };
}

// A link to the Settings tab that fixes a row (fixes: {metric id: "keys" | "models"}, from the server).
function fixLink(fixes, id) {
  const tab = fixes && fixes[id];
  return tab ? h("a", { class: "fix-link", href: `#/settings/${tab}` }, t(`w.fix.${id}`)) : null;
}

const ATTENTION = ["poor", "check"];

// Every part of the result folded, as the mentor asked: its name and a one-line summary ("All good", "1 Poor ·
// 2 Check"), opened one at a time by the person who wants the detail. Returns the cards and open(metricId), which
// opens the part holding that measure and points at it (from What to check).
function sections(rep, fixes) {
  const rows = {};
  const cards = rep.sections.filter(s => s.metrics.length).map(s => {
    const count = lv => s.metrics.filter(m => m.level === lv).length;
    const summary = ATTENTION.filter(count).map(lv => `${count(lv)} ${rep.badges?.[lv] ?? t(`verdict.${lv}`)}`);
    const graded = s.metrics.some(m => ["good", ...ATTENTION].includes(m.level));
    const mine = [];
    const card = h("details", { class: "card section fold" },
      h("summary", {}, h("h2", {}, s.title), h("span", { class: "grow" }),
        summary.length ? h("span", { class: `fold-count ${count("poor") ? "poor" : "check"}` }, summary.join(" · "))
          : h("span", { class: "fold-count muted" }, graded ? t("w.review.all_good") : t("w.review.info_only"))),
      s.metrics.map(m => {
        const row = h("details", { class: `metric ${m.level}`, open: fixes && fixes[m.id] ? true : null },
          h("summary", {}, h("span", { class: "label" }, m.label), badge(rep, m.level),
            h("span", { class: "display muted" }, m.display ?? ""), fixLink(fixes, m.id)),
          h("p", {}, m.message), m.thresholds ? h("p", { class: "muted small" }, m.thresholds) : null);
        mine.push([m.id, row]);
        return row;
      }));
    for (const [id, row] of mine) rows[id] = { row, card };
    return card;
  });
  return {
    cards,
    open(id) {
      const found = rows[id];
      if (!found) return;
      found.card.open = true;
      found.row.open = true;
      found.row.scrollIntoView({ behavior: "smooth", block: "center" });
      found.row.classList.remove("flash");
      void found.row.offsetWidth;                   // restart the highlight
      found.row.classList.add("flash");
    },
  };
}

// What needs a person, first: Poor, then Check. Each part's graded results that aren't Good (open the part to see how
// it's measured), then every moment to look at (click: the players and the timeline go there).
function whatToCheck(rep, onMeasure, onMoment) {
  const measures = rep.sections.flatMap(s => s.metrics.filter(m => ATTENTION.includes(m.level)));
  const moments = rep.things_to_check || [];
  if (!measures.length && !moments.length) return h("p", { class: "muted" }, rep.labels.nothing);
  const SHOWN = 3;                                   // items per level before "Show more"
  const group = lv => {
    const ms = measures.filter(m => m.level === lv), ts = moments.filter(x => x.severity === lv);
    if (!ms.length && !ts.length) return null;
    const items = [
      ...ms.map(m => h("li", {}, h("button", { type: "button", class: "item", onclick: () => onMeasure(m.id) },
        h("span", { class: "head" }, h("strong", {}, m.label)), h("span", { class: "why" }, m.message)))),
      ...ts.map(x => h("li", {}, h("button", { type: "button", class: "item", onclick: () => onMoment(x) },
        h("span", { class: "head" }, x.start != null ? h("span", { class: "time" }, fmtTime(x.start)) : null,
          h("strong", {}, x.category)), h("span", { class: "why" }, x.message))))];
    const list = h("ol", { class: "check-list" }, items.slice(0, SHOWN));
    let open = false;
    const toggle = items.length > SHOWN ? h("button", { type: "button", class: "link show-more", onclick: () => {
      open = !open;
      list.replaceChildren(...(open ? items : items.slice(0, SHOWN)));
      toggle.textContent = open ? t("w.review.show_less") : t("w.review.show_more", { n: items.length - SHOWN });
    } }, t("w.review.show_more", { n: items.length - SHOWN })) : null;
    return h("div", { class: `check-group ${lv}` },
      h("div", { class: "group-head" }, badge(rep, lv), h("span", { class: "group-count" }, String(items.length))),
      list, toggle);
  };
  return [group("poor"), group("check")];
}

// The result's title; a click turns it into a field (Enter or leaving it saves, Escape cancels).
function editableTitle(title, jobId, dub) {
  const heading = h("h1", { class: "editable", tabindex: "0", title: t("w.review.rename") }, title);
  const edit = () => {
    const field = h("input", { type: "text", class: "title-field", value: heading.textContent, maxlength: "200",
      "aria-label": t("w.review.rename") });
    let done = false;
    const finish = async save => {
      if (done) return;
      done = true;
      const value = field.value.trim();
      if (save && value && value !== heading.textContent) {
        try {
          const r = await api(`/api/jobs/${jobId}/title${dub ? `?dub=${dub}` : ""}`,
            { method: "PUT", body: JSON.stringify({ title: value }) });
          heading.textContent = r.title;
        } catch (e) { alert(e.message); }
      }
      field.replaceWith(heading);
      heading.focus();
    };
    field.addEventListener("keydown", e => {
      if (e.key === "Enter") finish(true);
      if (e.key === "Escape") finish(false);
      e.stopPropagation();                          // not the player's keys while typing
    });
    field.addEventListener("blur", () => finish(true));
    heading.replaceWith(field);
    field.focus();
    field.select();
  };
  heading.addEventListener("click", edit);
  heading.addEventListener("keydown", e => { if (e.key === "Enter") edit(); });
  return heading;
}

// dub names one dub of a comparison (A, B, ...); embedded leaves out the page's own "evaluate another" link.
export function renderReview(root, jobId, dub = null, embedded = false) {
  const q = dub ? `?dub=${dub}` : "";
  let ctl = null, alive = true, flow = null, setListen = null;
  const onKey = e => {
    if (!ctl || ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if (flow?.active && !e.ctrlKey && !e.metaKey && !e.altKey) {     // the review flow's keys work on its buttons too
      const act = { KeyN: flow.next, KeyP: flow.prev }[e.code];
      if (act) { e.preventDefault(); act(); return; }
    }
    if (document.activeElement?.tagName === "BUTTON") return;
    if (e.code === "Space") { e.preventDefault(); ctl.toggle(); }
    if (e.code === "ArrowLeft") ctl.seek(ctl.time - (e.shiftKey ? 5 : 1));
    if (e.code === "ArrowRight") ctl.seek(ctl.time + (e.shiftKey ? 5 : 1));
  };
  root.append(h("p", { class: "muted" }, t("w.review.loading")));

  api(`/api/jobs/${jobId}/report?lang=${state.lang}${dub ? `&dub=${dub}` : ""}`).then(data => {
    if (!alive) return;
    const rep = data.report, p = rep.project, o = rep.overall;
    const detail = detailPanel(data, voteStore(data, jobId, q));
    const clock = h("span", { class: "mono clock" }, "0:00.0");
    let tl = null;
    ctl = players(data, jobId, q, (s, playing) => {
      clock.textContent = `${fmtTime(s)} / ${fmtTime(data.duration_sec)}`;
      tl?.setTime(s, playing);
    });
    tl = timeline(data, s => ctl.seek(s), item => { tl.select(item); detail.show(item); });
    // The review flow shows each moment (selected on the timeline, its card, the videos at its start) and plays
    // nothing by itself: Play or Space does.
    flow = reviewFlow(rep, i => {
      tl.select({ kind: "issue", i });
      detail.show({ kind: "issue", i });
      if (ctl.playing) ctl.toggle();
      ctl.seek(rep.problem_intervals[i].start);
    });
    for (const side of ["original", "dub"])
      api(`/api/jobs/${jobId}/peaks/${side}${q}`).then(pk => alive && tl.setPeaks(side, pk)).catch(() => {});

    const listen = h("div", { class: "segmented", role: "group", "aria-label": t("w.review.listen") },
      ["original", "dub"].map(side => h("button", { type: "button", class: side === "dub" ? "on" : "",
        "data-side": side, onclick: () => setListen(side) }, side === "original" ? rep.labels.original : rep.labels.dub)));
    // Which track you hear; the buttons show it.
    setListen = side => {
      ctl.setListen(side);
      listen.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.side === side));
    };
    const playBtn = h("button", { type: "button", class: "primary", onclick: () => ctl.toggle() },
      t("w.review.play"));
    const label = () => { playBtn.textContent = ctl.playing ? t("w.review.pause") : t("w.review.play"); };
    for (const v of [ctl.original, ctl.dub]) for (const ev of ["play", "pause", "ended"]) v.addEventListener(ev, label);

    const parts = sections(rep, data.fixes);
    // A moment that is one of the timeline's problems is selected there too; any other goes to its time.
    const goTo = x => {
      const i = x.interval ? rep.problem_intervals.findIndex(iv => iv.start === x.interval.start
        && iv.end === x.interval.end && iv.category === x.interval.category) : -1;
      if (i >= 0) { tl.select({ kind: "issue", i }); detail.show({ kind: "issue", i }); }
      if (x.start != null) ctl.seek(x.start);
    };

    fill(root,
      h("section", { class: `verdict card ${o.level}` },
        h("div", { class: "row" }, editableTitle(p.title, jobId, dub), h("span", { class: "grow" }),
          h("div", { class: "head-actions" }, badge(rep, o.level),
            embedded ? null : h("a", { class: "button", href: "#/new" }, t("w.review.new")),
            embedded ? null : exportButton(jobId))),
        h("p", { class: "muted" }, [p.source_language || "?", "→", p.target_language || "?",
          p.duration_sec ? `· ${fmtTime(p.duration_sec)}` : ""].join(" ")),
        h("p", { class: "headline" }, o.headline), h("p", { class: "muted small" }, rep.counts_text)),
      h("section", { class: "editor card" },
        h("div", { class: "screens" },
          h("figure", {}, ctl.original, h("figcaption", {}, rep.labels.original)),
          h("figure", {}, ctl.dub, h("figcaption", {}, rep.labels.dub))),
        h("div", { class: "transport row" }, playBtn, clock, h("span", { class: "grow" }),
          h("span", { class: "muted small" }, t("w.review.listen")), listen,
          h("button", { type: "button", onclick: () => tl.zoomOut(), "aria-label": t("w.tl.zoom_out") }, "−"),
          h("button", { type: "button", onclick: () => tl.fit() }, t("w.tl.fit")),
          h("button", { type: "button", onclick: () => tl.zoomIn(), "aria-label": t("w.tl.zoom_in") }, "+")),
        tl.el,
        h("p", { class: "muted small" }, t("w.tl.help")),
        flow?.el),
      h("div", { class: "split" },
        h("section", { class: "card what-to-check" }, h("h2", {}, rep.labels.things),
          whatToCheck(rep, id => parts.open(id), goTo)),
        detail.el),
      h("div", { class: "details-head" }, h("h2", {}, t("w.review.details")),
        h("span", { class: "muted small" }, t("w.review.details_hint"))),
      ...parts.cards,
      rep.not_measured.length ? h("details", { class: "card section fold" },
        h("summary", {}, h("h2", {}, rep.labels.not_measured), h("span", { class: "grow" }),
          h("span", { class: "fold-count muted" }, String(rep.not_measured.length))),
        h("ul", {}, rep.not_measured.map(n => h("li", {}, h("strong", {}, n.label), " — ", n.reason)))) : null);
    document.addEventListener("keydown", onKey);
  }).catch(e => {
    if (alive) fill(root, h("p", { class: "error" }, e.message),
      h("a", { class: "button", href: "#/" }, t("w.progress.back")));
  });

  return () => { alive = false; ctl?.stop(); document.removeEventListener("keydown", onKey); };
}
