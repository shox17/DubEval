// The sidebar's foot, as in PersoDub: Help, Send feedback and the "What's new" card, plus updates.
//
// Updates come from the desktop app (desktop/preload.js puts window.dubevalShell on the page): it downloads a new
// version in the background and reports {phase, version, pct}; phase is idle | checking | none | downloading |
// ready | error. In a plain browser there is no shell, so nothing is announced and the card only shows the notes.
import { h, openModal, state, t } from "./app.js";

const shell = window.dubevalShell || null;
let update = { phase: "idle" };
const listeners = new Set();

// Calls fn(state, stop) with the update state now and on every change, until stop() is called.
export function watchUpdates(fn) {
  const entry = u => fn(u, stop);
  const stop = () => { listeners.delete(entry); };
  listeners.add(entry);
  fn(update, stop);
  return stop;
}

// Follows the update state for an element: fn(state) while it's on the page; stops once it has left the page. (The
// first call comes before the element is placed, so "not on the page" alone doesn't mean "gone".)
export function watchUpdatesFor(el, fn) {
  let shown = false;
  return watchUpdates((u, stop) => {
    if (el.isConnected) shown = true;
    else if (shown) { stop(); return; }
    fn(u);
  });
}

export const updatesAvailable = () => !!shell;
export const checkForUpdates = () => shell && shell.checkForUpdates();

function setUpdate(next) {
  update = next || { phase: "idle" };
  refreshSidebar();
  listeners.forEach(fn => fn(update));
  if (state.info) maybeAnnounce(update);
}

// The card's title and dot: "What's new in 0.1.0", or the update once there is one.
export function refreshSidebar() {
  const card = document.getElementById("nav-whats-new");
  if (!card || !state.info) return;
  const live = update.phase === "downloading" || update.phase === "ready";
  card.classList.toggle("live", live);
  card.title = live ? t("w.nav.update_available") : "";
  card.querySelector(".side-label").textContent = update.phase === "ready"
    ? t("w.nav.update_ready", { version: update.version }) : t("w.nav.whats_new", { version: state.info.version });
}

// Help, in PersoDub's shape: one darker panel of parts (a title, what it does, a grey line on how or where), then
// the user guide and the FAQ on GitHub.
function helpDialog() {
  const docs = name => `${state.info.repository}/blob/main/docs/${name}.md`;
  const link = (href, key) => h("a", { href, target: "_blank", rel: "noopener" }, t(key));
  openModal(t("w.help.title"), h("div", { class: "help-panel" },
    ["evaluate", "compare", "links", "where"].map(id => h("div", { class: "help-item" },
      h("b", {}, t(`w.help.${id}`)), h("p", {}, t(`w.help.${id}_text`)), h("p", { class: "help-more" }, t(`w.help.${id}_more`)))),
    h("p", { class: "help-links" }, link(docs("usage"), "w.help.guide"), " · ", link(docs("faq"), "w.help.faq"))),
  [{ label: t("w.ok"), primary: true }]);
}

const live = u => !!u.version && (u.phase === "downloading" || u.phase === "ready");

// "2026-10-26" in the viewer's own time zone, or "" for a date that can't be read.
function releaseDay(iso) {
  const d = new Date(iso || "");
  if (Number.isNaN(d.getTime())) return "";
  const two = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`;
}

// A release's notes as plain lines: electron-updater hands over the GitHub release body as HTML, a plain string, a
// list of {version, note}, or nothing. Tags are stripped and the lines are written as text, so nothing from the
// network becomes markup.
function noteLines(notes, version) {
  if (!notes) return [];
  if (Array.isArray(notes)) {
    const own = notes.find(n => n && n.version === version);
    notes = (own ? [own] : notes).map(n => (n && n.note) || "").join("\n");
  }
  const box = document.createElement("textarea");      // decodes entities without running anything
  box.innerHTML = String(notes).replace(/<(script|style)\b[\s\S]*?<\/\1\s*>/gi, "")
    .replace(/<\s*\/?\s*(br|p|li|ul|ol|div|h[1-6])\b[^>]*>/gi, "\n").replace(/<[^>]*>/g, "");
  return box.value.split(/\r?\n/).map(l => l.trim().replace(/^(#+|[-*•])\s+/, "").replace(/\*\*/g, "").trim())
    .filter(l => l && !/^what.?s new/i.test(l));
}

// Whether an evaluation is running now (restarting would stop it): a started draft's card says so.
async function evaluationRunning() {
  try {
    const list = await fetch("/api/evaluations", { credentials: "same-origin" }).then(r => r.json());
    return (list.drafts || []).some(d => d.state === "running");
  } catch { return false; }
}

// The "Version update" window, as PersoDub's: on the left whether DubEval is up to date, the versions and the
// restart; on the right What's new (the update's own notes once there is one, else this version's).
let windowOpen = false;
function versionWindow() {
  if (windowOpen) return;
  windowOpen = true;
  const title = h("h3", {});
  const current = h("p", { class: "muted" }, t("w.upd.current", { version: state.info.version }));
  const next = h("p", { class: "upd-next" });
  const go = h("button", { type: "button", class: "primary", hidden: true, onclick: () => shell.restartToUpdate() });
  const running = h("p", { class: "upd-running small", hidden: true }, t("w.upd.running_stops"));
  const check = h("button", { type: "button", class: "link", hidden: true, onclick: () => checkForUpdates() },
    t("w.upd.check"));
  const notes = h("ul", { class: "wn-list" });
  const link = h("a", { href: "#", target: "_blank", rel: "noopener", hidden: true }, t("w.upd.release_page"));
  const body = h("div", { class: "upd-body" },
    h("div", { class: "upd-left" }, title, current, next, h("span", { class: "grow" }), go, running, check),
    h("div", { class: "upd-right" }, h("span", { class: "upd-h muted" }, t("w.upd.whats_new")), notes, link));
  const close = openModal(t("w.upd.title"), body, [{ label: t("w.close") }], { width: 760 });
  const modal = body.closest(".modal");
  modal.classList.add("upd-modal");
  const done = () => { windowOpen = false; };
  new MutationObserver((_, obs) => { if (!modal.isConnected) { done(); obs.disconnect(); } })
    .observe(document.body, { childList: true });

  const paint = u => {
    const isLive = live(u);
    title.textContent = !shell ? `DubEval ${state.info.version}`
      : isLive ? t("w.upd.can_update")
      : u.phase === "checking" ? t("w.upd.checking")
      : u.phase === "error" ? t("w.upd.failed_short") : t("w.upd.up_to_date");
    const day = releaseDay(u.releaseDate);
    next.textContent = isLive ? t("w.upd.next", { version: u.version }) + (day ? ` · ${t("w.upd.released", { day })}` : "") : "";
    next.hidden = !isLive;
    go.hidden = !isLive;
    if (isLive) {
      const ready = u.phase === "ready";
      go.textContent = ready ? t("w.upd.restart") : t("w.upd.downloading", { pct: Math.round(u.pct || 0) });
      go.disabled = !ready;
    }
    check.hidden = !shell || isLive || u.phase === "checking";
    const lines = isLive ? noteLines(u.releaseNotes, u.version) : state.info.whats_new;
    notes.replaceChildren(...lines.map(n => h("li", {}, n)));
    link.hidden = !(isLive && !lines.length);
    if (!link.hidden) link.href = `${state.info.repository}/releases/tag/v${u.version}`;
  };
  watchUpdatesFor(body, paint);
  evaluationRunning().then(on => { running.hidden = !(on && live(update)); });
  return close;
}

// After an update: "Updated to 0.1.1 · What's new · ×" once, at the top of the work panel (as PersoDub).
const SEEN_KEY = "dubeval.seenVersion";
function updatedBanner() {
  let seen = null;
  try { seen = localStorage.getItem(SEEN_KEY); localStorage.setItem(SEEN_KEY, state.info.version); } catch { return; }
  if (!seen || seen === state.info.version) return;
  const banner = h("div", { class: "update-banner", role: "status" },
    h("span", {}, t("w.upd.updated", { version: state.info.version })),
    h("button", { type: "button", class: "link", onclick: () => { banner.remove(); versionWindow(); } }, t("w.upd.whats_new")),
    h("button", { type: "button", class: "link", "aria-label": t("w.close"), onclick: () => banner.remove() }, "×"));
  document.body.append(banner);
}

// The window opens by itself once a session, the first time an update is found while no other window is open.
let autoShown = false;
function maybeAnnounce(u) {
  if (autoShown || !live(u) || document.querySelector(".modal-overlay")) return;
  autoShown = true;
  versionWindow();
}

const SIDE_KEY = "dubeval.sideWidth";
const SIDE_MIN = 168, SIDE_MAX = 380, SIDE_DEFAULT = 200;

// The sidebar's width: dragged on its edge handle, or ←/→ on the focused handle; double-click resets it. Kept for
// the next launch.
function initResize() {
  const handle = document.getElementById("side-resize"), shell = document.querySelector(".shell");
  const set = (px, keep = true) => {
    const w = Math.round(Math.min(SIDE_MAX, Math.max(SIDE_MIN, px)));
    shell.style.setProperty("--side-width", `${w}px`);
    handle.setAttribute("aria-valuenow", String(w));
    if (keep) try { localStorage.setItem(SIDE_KEY, String(w)); } catch { /* not kept */ }
    return w;
  };
  let saved = SIDE_DEFAULT;
  try { saved = Number(localStorage.getItem(SIDE_KEY)) || SIDE_DEFAULT; } catch { /* storage may be blocked */ }
  set(saved, false);
  handle.setAttribute("aria-label", t("w.nav.resize"));
  handle.setAttribute("aria-valuemin", String(SIDE_MIN));
  handle.setAttribute("aria-valuemax", String(SIDE_MAX));
  handle.addEventListener("pointerdown", e => {
    e.preventDefault();
    handle.setPointerCapture(e.pointerId);
    handle.classList.add("dragging");
    const left = document.querySelector(".side").getBoundingClientRect().left;
    const move = ev => set(ev.clientX - left);
    const up = () => {
      handle.classList.remove("dragging");
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
  });
  handle.addEventListener("dblclick", () => set(SIDE_DEFAULT));
  handle.addEventListener("keydown", e => {
    const now = document.querySelector(".side").getBoundingClientRect().width;
    if (e.key === "ArrowLeft") { e.preventDefault(); set(now - 16); }
    if (e.key === "ArrowRight") { e.preventDefault(); set(now + 16); }
  });
}

export function initSidebar() {
  initResize();
  document.getElementById("nav-help").addEventListener("click", helpDialog);
  // DubEval has no feedback form of its own; the repository's issues page is where feedback goes (as in PersoDub).
  document.getElementById("nav-feedback").addEventListener("click", () =>
    window.open(`${state.info.repository}/issues`, "_blank", "noopener"));
  document.getElementById("nav-whats-new").addEventListener("click", versionWindow);
  updatedBanner();
  if (shell) {
    shell.onUpdate(setUpdate);
    shell.getUpdate().then(setUpdate).catch(() => {});
  }
  refreshSidebar();
}
