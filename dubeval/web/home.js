// Home screen, as PersoDub's: a banner that starts a new evaluation (and takes the dub: a file or any link), the ways to start,
// then every evaluation as a card with its picture. Drafts (a start page filled in but not run) come first; a draft
// that was started shows its progress and opens the progress screen. A card's "..." has Rename and Delete (a draft:
// Delete only). Cards come from /api/evaluations; the list refreshes while an evaluation is running.
import { api, confirmAlert, go, h, openModal, state, t } from "./app.js";

// No translation checker set up (a new install has no key): said where an evaluation starts, with the way to set one
// up. The check weighs most in the score and was off with only a grey line by the Start button to say so.
export function noCheckerNotice() {
  if ((state.info.judges || []).length) return null;
  return h("section", { class: "card skipped-banner no-checker", role: "note" },
    h("strong", {}, t("w.nocheck.title")), h("p", {}, t("w.nocheck.text")),
    h("p", { class: "row" }, h("a", { class: "button", href: "#/settings/keys" }, t("w.start.no_check_key")),
      h("a", { class: "button", href: "#/settings/models" }, t("w.start.no_check_local"))));
}

export const PREFILL_KEY = "dubeval.prefill";        // what the banner was given ({upload, name} or {link}): the dub
const POLL_MS = 2000;

function icon(paths, size = 16) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  for (const d of paths) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

const ICONS = {
  plus: ["M5 12h14", "M12 5v14"],
  link: ["M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1", "M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"],
  upload: ["M12 16V4", "m7 9 5-5 5 5", "M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"],
  one: ["M4 5h16v11H4z", "M8 20h8", "M12 16v4"],
  compare: ["M4 5h7v14H4z", "M13 5h7v14h-7z"],
  search: ["m21 21-4.34-4.34", "M11 3a8 8 0 1 0 0 16 8 8 0 0 0 0-16z"],
  more: ["M5 12h.01", "M12 12h.01", "M19 12h.01"],
  grid: ["M4 4h6v6H4z", "M14 4h6v6h-6z", "M4 14h6v6H4z", "M14 14h6v6h-6z"],
  list: ["M4 5h4v4H4z", "M4 15h4v4H4z", "M12 7h8", "M12 17h8"],
  check: ["m5 12 5 5 9-10"],
  chevron: ["m6 9 6 6 6-6"],
};

// Grid (the default) or List: kept in the browser, like the language, so it belongs to the page's address.
const VIEW_KEY = "dubeval.home.view";
function savedView() {
  try { return localStorage.getItem(VIEW_KEY) === "list" ? "list" : "grid"; } catch { return "grid"; }
}

// A language's name in the page's language, from its code; the English name the report kept otherwise.
// When a draft was saved, as the cards' dates read: the time today, else the date and time.
function savedAt(seconds) {
  const d = new Date(seconds * 1000), pad = n => String(n).padStart(2, "0");
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return d.toDateString() === new Date().toDateString() ? time
    : `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${time}`;
}

function langName(code, fallback) {
  if (code) {
    try { return new Intl.DisplayNames([state.lang], { type: "language" }).of(code) || fallback || code; } catch { /* below */ }
  }
  return fallback || "";
}

function fmtLength(sec) {
  if (!sec || !isFinite(sec)) return "";
  const s = Math.round(sec), m = Math.floor(s / 60);
  return `${m}:${String(s - m * 60).padStart(2, "0")}`;
}

// Adds a file chosen or dropped on the banner (as the start page does); resolves to {id: "upload:<id>", name}.
function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest(), form = new FormData();
    form.append("file", file);
    xhr.open("POST", "/api/uploads");
    xhr.setRequestHeader("Accept-Language", state.lang);
    xhr.upload.onprogress = e => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      xhr.status < 300 ? resolve({ id: data.id, name: data.name || file.name }) : reject(new Error(data.detail || xhr.statusText));
    };
    xhr.onerror = () => reject(new Error(t("w.err.upload")));
    xhr.send(form);
  });
}

// The banner takes the dub, a file or any kind of link, and opens the start page with it in the dub's card.
function banner(alive) {
  const link = h("input", { type: "url", placeholder: t("w.home.link"), "aria-label": t("w.home.link"),
    autocomplete: "off" });
  const startWith = given => {
    try { sessionStorage.setItem(PREFILL_KEY, JSON.stringify(given)); } catch { /* the start page just opens empty */ }
    go("#/new");
  };
  const useLink = () => {
    const value = link.value.trim();
    if (value) startWith({ link: value });
  };
  const status = h("div", { class: "home-banner-status", hidden: true });
  const fileInput = h("input", { type: "file", accept: "video/*,audio/*", class: "sr", tabindex: "-1" });
  async function useFile(file) {
    status.hidden = false;
    status.textContent = t("w.home.uploading");
    try {
      const added = await uploadFile(file, f => { status.textContent = `${t("w.home.uploading")} ${Math.round(f * 100)}%`; });
      if (alive()) startWith({ upload: added.id, name: added.name });
    } catch (e) {
      status.textContent = e.message;
    }
  }
  fileInput.addEventListener("change", () => fileInput.files[0] && useFile(fileInput.files[0]));
  const uploadBtn = h("button", { type: "button", class: "home-upload", onclick: () => fileInput.click() },
    icon(ICONS.upload, 14), t("w.home.upload"));
  link.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); useLink(); } });
  link.addEventListener("paste", () => setTimeout(() => alive() && useLink(), 0));
  const field = h("label", { class: "home-link" }, icon(ICONS.link, 14), link);
  const inputs = h("div", { class: "home-inputs" }, uploadBtn, field);
  // The inputs sit in the banner, whose own click opens the start page: clicks in them stay in them. That includes the
  // hidden file field: its click (the one that opens the file picker) would otherwise reach the banner and leave Home
  // before a file is chosen.
  for (const el of [inputs, status, fileInput]) for (const ev of ["click", "mousedown"]) el.addEventListener(ev, e => e.stopPropagation());
  const el = h("div", { class: "home-banner", role: "button", tabindex: "0", "aria-label": t("w.nav.new"),
    onclick: () => go("#/new"), onkeydown: e => { if (e.key === "Enter" && e.target === e.currentTarget) go("#/new"); } },
    h("div", { class: "home-banner-head" }, h("span", { class: "home-banner-plus" }, icon(ICONS.plus, 18)),
      h("span", {}, t("w.nav.new"))),
    h("div", { class: "home-banner-sub" }, t("w.home.banner_sub")), inputs, status, fileInput);
  // A video dropped anywhere on the banner is the dub.
  el.addEventListener("dragover", e => { e.preventDefault(); el.classList.add("over"); });
  el.addEventListener("dragleave", () => el.classList.remove("over"));
  el.addEventListener("drop", e => {
    e.preventDefault();
    el.classList.remove("over");
    if (e.dataTransfer.files[0]) useFile(e.dataTransfer.files[0]);
  });
  return el;
}

function toolCard(paths, title, desc, hash) {
  return h("button", { type: "button", class: "home-card", onclick: () => go(hash) },
    h("span", { class: "home-card-icon" }, icon(paths, 18)),
    h("span", { class: "home-card-title" }, title), h("span", { class: "home-card-desc" }, desc));
}

export function renderHome(root) {
  let alive = true, timer = null, data = { drafts: [], evaluations: [] }, query = "", renaming = null;
  const isAlive = () => alive;
  const count = h("span", { class: "projects-count" });
  const searchInput = h("input", { type: "search", placeholder: t("w.home.search_ph"), "aria-label": t("w.home.search_ph") });
  const searchBox = h("div", { class: "projects-search", hidden: true }, icon(ICONS.search, 14), searchInput);
  const searchBtn = h("button", { type: "button", class: "home-sbtn", onclick: () => {
    searchBox.hidden = !searchBox.hidden;
    if (!searchBox.hidden) searchInput.focus();
    else { searchInput.value = ""; query = ""; paint(); }
  } }, icon(ICONS.search, 14), t("w.home.search"));
  searchInput.addEventListener("input", () => { query = searchInput.value.trim().toLowerCase(); paint(); });
  const grid = h("div", { class: "projects-grid" }, h("div", { class: "projects-empty" }, t("w.loading")));
  const menu = h("div", { class: "proj-menu", role: "menu", hidden: true });
  let menuAnchor = null, view = savedView();

  const closeMenu = () => { menu.hidden = true; menu.replaceChildren(); menuAnchor?.setAttribute("aria-expanded", "false"); menuAnchor = null; };
  const onDocClick = e => { if (!menu.contains(e.target)) closeMenu(); };
  const onKey = e => { if (e.key === "Escape") closeMenu(); };
  document.addEventListener("click", onDocClick);
  document.addEventListener("keydown", onKey);

  // The view button shows the current view's icon; its menu lists Grid and List with a tick on the current one.
  const viewBtn = h("button", { type: "button", class: "home-sbtn home-view", "aria-haspopup": "menu", "aria-expanded": "false",
    "aria-label": t("w.home.view"), title: t("w.home.view"), onclick: e => {
      e.stopPropagation();
      if (menuAnchor === viewBtn) { closeMenu(); return; }
      openMenu(viewBtn, [["grid", "w.home.grid"], ["list", "w.home.list"]].map(([v, key]) =>
        [t(key), () => setView(v), view === v, ICONS[v]]));
    } });
  function setView(v) {
    view = v;
    try { localStorage.setItem(VIEW_KEY, v); } catch { /* the choice just isn't kept */ }
    grid.classList.toggle("list", v === "list");
    viewBtn.replaceChildren(icon(ICONS[v], 14), icon(ICONS.chevron, 12));
  }
  setView(view);

  // items: [label, run] or [label, run, checked, icon] (a choice: a tick shows on the checked one).
  function openMenu(anchor, items) {
    closeMenu();
    menu.replaceChildren(...items.map(([label, fn, checked, glyph]) => h("button", {
      type: "button", role: checked === undefined ? "menuitem" : "menuitemradio",
      ...(checked === undefined ? {} : { "aria-checked": String(checked), class: "menu-choice" }),
      onclick: e => { e.stopPropagation(); closeMenu(); fn(); } },
      ...(checked === undefined ? [label] : [h("span", { class: "menu-tick" }, checked ? icon(ICONS.check, 14) : null),
        glyph ? icon(glyph, 14) : null, label]))));
    menuAnchor = anchor;
    anchor.setAttribute("aria-expanded", "true");
    menu.hidden = false;
    // Under the button, or above it when the window ends first (a card on the last row); never past the right edge.
    const r = anchor.getBoundingClientRect(), m = menu.getBoundingClientRect(), gap = 4, edge = 8;
    const below = r.bottom + gap + m.height <= window.innerHeight - edge;
    menu.style.left = `${Math.max(edge, Math.min(r.left, window.innerWidth - m.width - edge))}px`;
    menu.style.top = `${below ? r.bottom + gap : Math.max(edge, r.top - gap - m.height)}px`;
    menu.querySelector("button")?.focus();
  }

  // Asked in PersoDub's alert shape; the dialog stays open with the reason when deleting fails.
  async function confirmDelete(title, text, run) {
    if (await confirmAlert({ title, text, keep: t("w.cancel"), confirm: t("w.home.delete"), onConfirm: run })) load();
  }

  async function openEvaluation(c, el) {
    el.setAttribute("aria-busy", "true");
    try {
      const job = await api(`/api/evaluations/${encodeURIComponent(c.id)}/open`, { method: "POST" });
      go(job.kind === "comparison" ? `#/compare/${job.id}/A` : `#/report/${job.id}`);
    } catch (e) {
      el.removeAttribute("aria-busy");
      openModal(t("w.nav.evaluations"), h("p", {}, e.message), [{ label: t("w.close"), primary: true }]);
      load();
    }
  }

  async function saveTitle(c, value) {
    renaming = null;
    const title = value.trim();
    if (title && title !== c.title) {
      try {
        await api(`/api/evaluations/${encodeURIComponent(c.id)}/title`, { method: "PUT", body: JSON.stringify({ title }) });
        c.title = title;
      } catch (e) {
        openModal(t("w.home.rename"), h("p", {}, e.message), [{ label: t("w.close"), primary: true }]);
      }
    }
    paint();
  }

  // One card: picture (with a chip top-left and the length bottom-right), then the name, one line under it and "...".
  function cardEl({ key, name, thumb, chip, chipClass, length, score, meta, open, menuItems }) {
    const nameEl = renaming === key
      ? h("input", { class: "proj-rename", maxlength: "200", value: name, "aria-label": t("w.home.rename") })
      : h("div", { class: "proj-name", title: name }, name);
    const more = h("button", { type: "button", class: "proj-more", "aria-haspopup": "menu",
      "aria-label": t("w.home.more", { name }), onclick: e => { e.stopPropagation(); openMenu(more, menuItems); } },
      icon(ICONS.more, 14));
    const img = thumb ? h("img", { class: "proj-img", src: thumb, alt: "", loading: "lazy" }) : null;
    if (img) img.addEventListener("error", () => img.remove());
    const el = h("div", { class: "proj-card", tabindex: "0", role: "button", "aria-label": t("w.home.open", { name }) },
      h("div", { class: "proj-thumb" }, img,
        chip ? h("span", { class: `proj-chip ${chipClass || ""}` }, chip) : null,
        length ? h("span", { class: "proj-dur" }, length) : null,
        // the quality score on the picture, like the length: in the line under it, it pushed the date out of sight
        score ? h("span", { class: "proj-score" }, score) : null),
      h("div", { class: "proj-row" }, h("div", { class: "proj-info" }, nameEl, h("div", { class: "proj-meta", title: meta }, meta)),
        more));
    el.addEventListener("click", e => { if (!e.target.closest(".proj-rename")) open(el); });
    el.addEventListener("keydown", e => { if (e.key === "Enter" && e.target === el) open(el); });
    return el;
  }

  function draftCard(d) {
    const name = d.name || t("w.home.untitled");
    const chip = { draft: t("w.home.draft"), running: t("w.home.running", { pct: Math.round((d.progress || 0) * 100) }),
      queued: d.queue_position ? t("w.home.queued_n", { n: d.queue_position }) : t("w.home.queued"), failed: t("w.home.failed"), stopped: t("w.home.stopped") }[d.state];
    const live = d.state === "running" || d.state === "queued";
    const saved = d.updated ? t("w.home.saved", { time: savedAt(d.updated) }) : null;
    const meta = live ? (d.dubs > 1 ? t("w.home.compared", { n: d.dubs }) : t("w.home.not_run"))
      : d.state === "draft" ? (saved ? t("w.home.draft_saved", { time: savedAt(d.updated) }) : t("w.home.not_run"))
        : t("w.home.retry");
    const del = () => confirmDelete(t("w.home.delete_draft_title"), t("w.home.delete_draft_text", { name }),
      () => api(`/api/drafts/${encodeURIComponent(d.id)}`, { method: "DELETE" }));
    return cardEl({ key: `d:${d.id}`, name, thumb: d.thumbnail, chip,
      chipClass: { running: "run", queued: "run", failed: "bad", stopped: "bad" }[d.state] || "muted", meta,
      open: () => go(live ? `#/job/${d.job_id}` : `#/draft/${d.id}`),
      // A running or waiting evaluation can't be deleted from here (stop it on its progress screen first).
      menuItems: live ? [[t("w.home.open", { name }), () => go(`#/job/${d.job_id}`)]] : [[t("w.home.delete"), del]] });
  }

  function evaluationCard(c) {
    const name = c.title || t("w.home.untitled");
    const langs = [langName(c.source_language_code, c.source_language), langName(c.target_language_code, c.target_language)]
      .filter(Boolean).join(" → ");
    // A comparison's verdict and score are its first place's: the card says whose ("A · 89 / 100").
    const whose = text => (text && c.kind === "comparison" && c.lead_dub ? t("w.home.of_dub", { d: c.lead_dub, text }) : text);
    const score = whose(c.score ? t(c.score.provisional ? "w.home.score_provisional" : "w.home.score", { score: c.score.value })
      : null);
    const meta = [c.kind === "comparison" ? t("w.home.compared", { n: c.dubs }) : langs, (c.created || "").slice(0, 10)]
      .filter(Boolean).join(" · ");
    const key = `e:${c.id}`;
    const el = cardEl({ key, name, thumb: `/api/evaluations/${encodeURIComponent(c.id)}/thumb`,
      chip: whose(c.verdict ? t(`verdict.${c.verdict}`) : null), chipClass: `verdict-${c.verdict}`,
      length: fmtLength(c.duration_sec), score, meta, open: card => openEvaluation(c, card),
      menuItems: [
        [t("w.home.rename"), () => { renaming = key; paint(); }],
        [t("w.home.delete"), () => confirmDelete(t("w.home.delete_title"), t("w.home.delete_text", { name }),
          () => api(`/api/evaluations/${encodeURIComponent(c.id)}`, { method: "DELETE" }))],
      ] });
    const input = el.querySelector(".proj-rename");
    if (input) {
      let done = false;
      const finish = save => { if (done) return; done = true; save ? saveTitle(c, input.value) : (renaming = null, paint()); };
      input.addEventListener("keydown", e => {
        if (e.key === "Enter") { e.preventDefault(); finish(true); }
        if (e.key === "Escape") { e.preventDefault(); finish(false); }
      });
      input.addEventListener("blur", () => finish(true));
      setTimeout(() => { input.focus(); input.select(); }, 0);
    }
    return el;
  }

  function paint() {
    const match = x => !query || (x || "").toLowerCase().includes(query);
    const drafts = data.drafts.filter(d => match(d.name));
    const done = data.evaluations.filter(c => match(c.title));
    const all = data.drafts.length + data.evaluations.length;
    const shown = drafts.length + done.length;
    count.textContent = all ? (query ? t("w.home.count", { shown, all }) : String(all)) : "";
    searchBtn.hidden = viewBtn.hidden = !all;                // nothing to search or lay out yet
    grid.replaceChildren(...(shown ? [...drafts.map(draftCard), ...done.map(evaluationCard)]
      : [h("div", { class: "projects-empty" }, all ? t("w.home.no_match") : t("w.home.empty"))]));
  }

  async function load() {
    clearTimeout(timer);
    try {
      const next = await api("/api/evaluations");
      if (!alive) return;
      data = next;
      if (renaming === null) paint();             // don't redraw under someone typing a new name
    } catch (e) {
      if (alive) grid.replaceChildren(h("p", { class: "error" }, e.message));
    }
    if (alive && data.drafts.some(d => d.state === "running" || d.state === "queued")) timer = setTimeout(load, POLL_MS);
  }

  root.append(h("div", { class: "home" },
    banner(isAlive),
    noCheckerNotice(),
    h("div", { class: "home-cards" },
      toolCard(ICONS.one, t("w.help.evaluate"), t("w.home.one_desc"), "#/new"),
      toolCard(ICONS.compare, t("w.help.compare"), t("w.home.compare_desc"), "#/new/compare")),
    h("div", { class: "projects-head" }, h("h3", {}, t("w.nav.evaluations")), count, h("span", { class: "grow" }), searchBtn, viewBtn),
    searchBox, grid), menu);
  load();
  return () => {
    alive = false;
    clearTimeout(timer);
    document.removeEventListener("click", onDocClick);
    document.removeEventListener("keydown", onKey);
    menu.remove();
  };
}
