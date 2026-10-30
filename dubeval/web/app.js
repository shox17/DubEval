// DubEval web interface: routing, texts and the server API. Screens live in home.js, start.js, progress.js, review.js.
import { renderHome } from "./home.js";
import { renderStart } from "./start.js";
import { renderProgress } from "./progress.js";
import { renderReview } from "./review.js";
import { renderCompare } from "./compare.js";
import { renderHistory } from "./history.js";
import { discardChanges, renderSettings, saveChanges, watchChanges } from "./settings.js";
import { initSidebar, refreshSidebar } from "./shell.js";

const LANG_KEY = "dubeval.lang";
export const state = { lang: "en", texts: {}, info: null, cleanup: null };

// Text by key with {placeholders}; falls back to the key so a missing text is easy to spot.
export function t(key, values = {}) {
  const s = state.texts[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (m, k) => (k in values ? values[k] : m));
}

export async function api(path, options = {}) {
  const headers = { "Accept-Language": state.lang };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { credentials: "same-origin", ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(" ") : data.detail;
    const error = new Error(detail || `${res.status} ${res.statusText}`);
    error.status = res.status;
    throw error;
  }
  return data;
}

// h("div", {class: "x", onclick}, child, ...): a small element builder (text children are escaped).
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;     // not an attribute: the page's policy blocks style="…"
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) if (c !== null && c !== undefined && c !== false)
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}

export function fmtTime(sec) {
  if (sec === null || sec === undefined || !isFinite(sec)) return "–";
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return `${m}:${s.toFixed(1).padStart(4, "0")}`;
}

// Replaces el's children, skipping empty ones (null, false) and flattening lists.
export function fill(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter(c => c !== null && c !== undefined && c !== false));
}

export const INFO_EVENT = "dubeval:info";         // sent after loadInfo(): keys, models or the language changed

// Opens a screen. Under an open Settings dialog the screen changes beneath it and the dialog stays (closing it
// shows the new address); replace: true leaves no step in the browser history (Back doesn't come back here).
export function go(hash, { replace = false } = {}) {
  if (settings) { drawScreen(hash); markNav("settings"); return; }
  if (replace) location.replace(hash); else location.hash = hash;
}

// Whether overlay is the dialog on top (Escape closes only that one, not a dialog under it).
const onTop = overlay => [...document.querySelectorAll(".modal-overlay")].pop() === overlay;

// Changes the address of the screen on show without drawing it again (a new draft gets its own address).
export function setAddress(hash) {
  rendered = hash;
  history.replaceState(null, "", hash);
}

// A dialog in PersoDub's shape: a title bar, the body, buttons on the right. Escape or a click outside closes it.
// buttons: [{label, primary, onclick(close)}]; returns close().
export function openModal(title, body, buttons = [], { width = null } = {}) {
  const close = () => { overlay.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = e => { if (e.key === "Escape" && onTop(overlay)) close(); };
  const foot = buttons.map(b => h("button", { type: "button", class: b.primary ? "primary" : "",
    hidden: b.hidden, onclick: () => (b.onclick ? b.onclick(close) : close()) }, b.label));
  const modal = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title,
    style: width ? `width: min(${width}px, 92vw)` : null },
    h("div", { class: "modal-head" }, h("h2", {}, title)),
    h("div", { class: "modal-body" }, body),
    h("div", { class: "modal-foot" }, foot));
  const overlay = h("div", { class: "modal-overlay", onclick: e => { if (e.target === overlay) close(); } }, modal);
  document.addEventListener("keydown", onKey);
  document.body.append(overlay);
  (foot.find(b => b.classList.contains("primary")) || foot[0])?.focus();
  return close;
}

// A question before something that can't be undone, in PersoDub's alert shape: a warning sign, the question, one line
// under it and two buttons side by side (the safe one first). Resolves to true when confirmed. onConfirm, when given,
// runs before the dialog closes; an error it throws is shown in the dialog, which stays open. signal (an AbortSignal)
// closes it unanswered (false) when what it asks about is over, e.g. the evaluation finished while it was open.
export function confirmAlert({ title, text = "", keep, confirm, onConfirm = null, signal = null }) {
  return new Promise(resolve => {
    const sign = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    sign.setAttribute("viewBox", "0 0 24 24");
    sign.setAttribute("class", "alert-tri");
    sign.setAttribute("aria-hidden", "true");
    for (const d of ["m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3", "M12 9v4", "M12 17h.01"]) {
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", d);
      sign.append(p);
    }
    const error = h("p", { class: "error small", role: "alert" });
    const done = answer => { overlay.remove(); document.removeEventListener("keydown", onKey); resolve(answer); };
    const onKey = e => { if (e.key === "Escape" && onTop(overlay)) done(false); };
    const yes = h("button", { type: "button", class: "primary", onclick: async () => {
      if (!onConfirm) return done(true);
      yes.disabled = no.disabled = true;
      try { await onConfirm(); done(true); } catch (e) { error.textContent = e.message; yes.disabled = no.disabled = false; }
    } }, confirm);
    const no = h("button", { type: "button", onclick: () => done(false) }, keep);
    const modal = h("div", { class: "modal modal-alert", role: "alertdialog", "aria-modal": "true", "aria-label": title },
      h("div", { class: "modal-body" }, h("div", { class: "alert-icon" }, sign), h("h2", {}, title),
        text ? h("p", {}, text) : null, error),
      h("div", { class: "modal-foot" }, no, yes));
    const overlay = h("div", { class: "modal-overlay", onclick: e => { if (e.target === overlay) done(false); } }, modal);
    document.addEventListener("keydown", onKey);
    document.body.append(overlay);
    yes.focus();
    if (signal) {
      if (signal.aborted) done(false);
      else signal.addEventListener("abort", () => { if (overlay.isConnected) done(false); }, { once: true });
    }
  });
}

// Switches the interface language (Settings → About), keeps it for next time and redraws the screen.
export async function setLanguage(code) {
  state.lang = code;
  try { localStorage.setItem(LANG_KEY, code); } catch { /* not kept */ }
  await loadInfo();
  route(true);
}

// Reloads the texts and what's installed (after a download finishes, for example).
export async function loadInfo() {
  state.info = await api(`/api/info?lang=${state.lang}`);
  window.dispatchEvent(new Event(INFO_EVENT));      // the start page updates its checker list, for example
  state.texts = state.info.texts;
  document.documentElement.lang = state.lang;
  const label = (id, text) => { document.querySelector(`#${id} .side-label`).textContent = text; };
  label("nav-new", t("w.nav.new"));
  label("nav-home", t("w.nav.home"));
  label("nav-history", t("h.title"));
  label("nav-settings", t("w.set.title"));
  label("nav-help", t("w.nav.help"));
  label("nav-feedback", t("w.nav.feedback"));
  document.getElementById("nav-github").textContent = t("w.nav.github");
  document.querySelectorAll(".repo-link").forEach(a => { a.href = state.info.repository; });
  refreshSidebar();
}

// Lights the sidebar entry of the screen on show: the start page and drafts belong to "New evaluation"; the home
// screen and every evaluation (its progress, review or comparison) to "Evaluations".
function markNav(screen) {
  const on = { history: "nav-history", settings: "nav-settings", new: "nav-new", draft: "nav-new" }[screen] || "nav-home";
  document.querySelectorAll(".side a").forEach(a => a.classList.toggle("on", a.id === on));
}

// Settings opens as a dialog over the screen it was opened from (as in PersoDub); #/settings/<tab> picks the tab.
// Closing it puts that screen's address back without drawing the screen again.
let rendered = null;                                 // the address of the screen drawn under any dialog
let settings = null;                                 // the open Settings dialog: {overlay, body, title, cleanup}

function closeSettings(restore = true) {
  if (!settings) return;
  discardChanges();                                  // Cancel, Escape or a click outside: what Save would keep goes
  settings.cleanup?.();
  settings.overlay.remove();
  document.removeEventListener("keydown", settings.onKey);
  settings = null;
  if (!restore) return;                              // the address already names the next screen
  history.replaceState(null, "", rendered || "#/");
  markNav((rendered || "#/").split("/")[1]);
}

function openSettings(tab) {
  if (!settings) {
    const body = h("div", { class: "modal-body" });
    const title = h("h2", {}, t("w.set.title"));
    const error = h("p", { class: "error small set-error", role: "alert" });
    const cancel = h("button", { type: "button", onclick: closeSettings }, t("w.cancel"));
    // Save keeps the typed keys and a new language, then closes; a key the server refuses keeps the dialog open.
    const save = h("button", { type: "button", class: "primary", disabled: true, onclick: async () => {
      save.disabled = cancel.disabled = true;
      error.textContent = "";
      try {
        const lang = await saveChanges();
        closeSettings();
        if (lang) await setLanguage(lang); else await loadInfo().catch(() => {});
      } catch (e) {
        error.textContent = e.message;
        cancel.disabled = false;
        save.disabled = false;
      }
    } }, t("w.set.save"));
    const modal = h("div", { class: "modal settings-modal", role: "dialog", "aria-modal": "true", "aria-label": t("w.set.title") },
      h("div", { class: "modal-head" }, title), body, error,
      h("div", { class: "modal-foot" }, cancel, save));
    const overlay = h("div", { class: "modal-overlay", onclick: e => { if (e.target === overlay) closeSettings(); } }, modal);
    const onKey = e => { if (e.key === "Escape" && onTop(overlay)) closeSettings(); };
    document.addEventListener("keydown", onKey);
    document.body.append(overlay);
    settings = { overlay, body, title, onKey, cleanup: null };
    watchChanges(on => { save.disabled = !on; });
  }
  settings.cleanup?.();
  settings.title.textContent = t("w.set.title");
  settings.body.replaceChildren();
  settings.cleanup = renderSettings(settings.body, tab);
  markNav("settings");
}

function route(force = false) {
  const [, screen, id] = location.hash.split("/");
  if (screen === "downloads") {                      // the old Downloads page now lives in Settings → Models
    history.replaceState(null, "", "#/settings/models");
    return route(force);
  }
  if (screen === "settings") {
    if (rendered === null || force) drawScreen(rendered || "#/");   // opened straight away: the start page below
    openSettings(id);
    return;
  }
  const target = location.hash;                      // read first: closing Settings must not put the old address back
  closeSettings(false);
  drawScreen(target);
}

function drawScreen(hash) {
  rendered = hash;
  if (state.cleanup) { state.cleanup(); state.cleanup = null; }
  const root = document.getElementById("app");
  root.replaceChildren();
  const [, screen, id, dub] = hash.split("/");
  markNav(screen);
  // Results, the home screen and the history use the whole window (they stretch with it, as PersoDub's home).
  root.classList.toggle("wide", ["report", "compare", "history", "", undefined].includes(screen));
  root.scrollTop = 0;                               // the work panel scrolls, not the window
  if (screen === "job" && id) state.cleanup = renderProgress(root, id);
  else if (screen === "report" && id) state.cleanup = renderReview(root, id);
  else if (screen === "compare" && id) state.cleanup = renderCompare(root, id, dub);
  else if (screen === "history") state.cleanup = renderHistory(root);
  else if (screen === "new") state.cleanup = renderStart(root, { compare: id === "compare" });
  else if (screen === "draft" && id) state.cleanup = renderStart(root, { draftId: id });
  else state.cleanup = renderHome(root);
}

function pickLanguage(languages) {
  let saved = null;
  try { saved = localStorage.getItem(LANG_KEY); } catch { /* storage may be blocked */ }
  const browser = (navigator.language || "en").split("-")[0];
  return [saved, browser].find(l => l && l in languages) || "en";
}

// The boot screen's words, before the server's texts arrive (the same as the desktop shell's starting page).
const BOOT_TEXT = {
  en: ["Starting DubEval…", "Loading the speech and video tools. The first start can take up to a minute."],
  ko: ["DubEval 시작 중…", "음성·영상 도구를 불러오고 있습니다. 처음 시작할 때는 1분 정도 걸릴 수 있습니다."],
  pt: ["Iniciando o DubEval…", "Carregando as ferramentas de fala e vídeo. A primeira vez pode levar até um minuto."],
  es: ["Iniciando DubEval…", "Cargando las herramientas de habla y video. La primera vez puede tardar hasta un minuto."],
};

function showBoot(lang) {
  const [title, text] = BOOT_TEXT[lang] || BOOT_TEXT.en;
  document.getElementById("boot-title").textContent = title;
  document.getElementById("boot-text").textContent = text;
}

// The app appears only once its texts and first screen are in place: never a frame without its labels.
function hideBoot() {
  document.body.classList.remove("booting");
  document.getElementById("boot")?.remove();
}

async function main() {
  try {
    state.lang = pickLanguage({ en: 1, ko: 1, pt: 1, es: 1 });
    showBoot(state.lang);
    await loadInfo();
  } catch (e) {
    document.getElementById("boot-text").textContent = e.message;
    document.getElementById("boot").classList.add("failed");
    return;
  }
  initSidebar();
  window.addEventListener("hashchange", () => route());
  route();
  hideBoot();
}

main();
