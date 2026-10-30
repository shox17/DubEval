// Settings, laid out like PersoDub's: one row of tabs (API keys, Models, Storage, Privacy, About), one darker panel
// that scrolls, Cancel and Save. Models and Storage are lists of bands (a group and its size) over rows of
// name | size | state | button; the other tabs are "label | control" rows. Keys are written once and never shown back;
// models download with progress, stop and resume.
import { api, confirmAlert, fill, h, loadInfo, state, t } from "./app.js";
import { checkForUpdates, updatesAvailable, watchUpdatesFor } from "./shell.js";

const TABS = ["keys", "models", "storage", "privacy", "about"];
const POLL_MS = 1000;
const PROVIDERS = [
  { id: "anthropic", judge: "claude", link: "https://console.anthropic.com/settings/keys" },
  { id: "gemini", judge: "gemini", link: "https://aistudio.google.com/apikey" },
  { id: "openai", judge: "openai", link: "https://platform.openai.com/api-keys" },
];
const LICENSES = [
  ["faster-whisper / CTranslate2", "MIT"], ["Whisper models", "MIT"], ["BGE-M3", "MIT"],
  ["WeSpeaker ResNet34", "CC BY 4.0"], ["DNSMOS P.835", "CC BY 4.0"], ["MediaPipe Face Landmarker", "Apache-2.0"],
  ["LatentSync StableSyncNet (download)", "CreativeML OpenRAIL++-M"],
  ["librosa", "ISC"], ["onnxruntime", "MIT"], ["FFmpeg", "LGPL / GPL"], ["Onest typeface", "OFL-1.1"],
  ["Electron", "MIT"], ["PersoDub (design, icon)", "AGPL-3.0 / ESTsoft"],
];

const gb = bytes => (bytes == null ? "—" : bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB`
  : `${Math.max(1, Math.round(bytes / 1e6))} MB`);
const row = (label, ...control) => h("div", { class: "set-row" }, h("span", {}, label),
  h("div", { class: "set-ctl" }, ...control));
// A band over a list: the group's name and its size (PersoDub's Models list).
const band = (name, size) => h("div", { class: "model-group-head" }, h("span", {}, name), h("span", { class: "model-size" }, size));
const ready = () => h("span", { class: "model-ok" }, t("w.mod.ready"));

// ---------- Save and Cancel ----------
// What Save keeps: API keys typed in and a new interface language. Everything else happens at once, as in PersoDub
// (a download, removing a key, clearing downloads). Cancel, Escape or a click outside forgets what Save would keep.
const pending = { keys: {}, lang: null };
let onChange = () => {};
const dirty = () => Object.values(pending.keys).some(v => v.trim()) || (pending.lang !== null && pending.lang !== state.lang);
const changed = () => onChange(dirty());

// fn(dirty) runs now and on every change, so the dialog's Save is on only when there is something to save.
export function watchChanges(fn) { onChange = fn; changed(); }
export function discardChanges() { pending.keys = {}; pending.lang = null; changed(); }
// Saves the typed keys (the server checks each one; the first it refuses throws, the rest stay to fix) and returns
// the language to switch to, if a new one was chosen.
export async function saveChanges() {
  for (const [id, key] of Object.entries(pending.keys)) {
    if (!key.trim()) continue;
    try {
      await api(`/api/settings/keys/${id}`, { method: "PUT", body: JSON.stringify({ key }) });
    } catch (e) { throw new Error(`${t(`w.set.${id}.title`)}: ${e.message}`); }
    delete pending.keys[id];
  }
  const lang = pending.lang !== state.lang ? pending.lang : null;
  pending.lang = null;
  changed();
  return lang;
}

// ---------- Models ----------
function modelsTab(panel, timers, alive) {
  async function load(errors = {}) {
    for (const timer of timers) clearTimeout(timer);
    timers.clear();
    let data;
    try { data = await api("/api/models"); } catch (e) { fill(panel, h("p", { class: "error" }, e.message)); return; }
    if (!alive()) return;
    const out = [h("div", { class: "set-summary" }, t("w.mod.summary", { n: data.ready, size: gb(data.bytes) }))];
    for (const group of data.groups) {
      const total = group.rows.filter(r => ["builtin", "installed"].includes(r.state)).reduce((a, r) => a + (r.bytes || 0), 0);
      out.push(band(t(`w.mod.group.${group.id}`), total ? gb(total) : ""),
        h("div", { class: "model-rows" }, group.rows.map(m => modelRow(m, errors[m.id]))));
    }
    fill(panel, out);
  }

  function follow(m, bar, line) {
    const tick = async () => {
      timers.delete(timer);
      if (!alive()) return;
      let job;
      try { job = await api(`/api/jobs/${m.job}?lang=${state.lang}`); } catch { return; }
      if (job.status === "running") {
        bar.value = job.progress;
        line.textContent = `${job.message} ${Math.round(job.progress * 100)}%`;
        timer = setTimeout(tick, POLL_MS);
        timers.add(timer);
      } else {
        await loadInfo().catch(() => {});
        load(job.status === "failed" ? { [m.id]: job.error } : {});
      }
    };
    let timer = setTimeout(tick, 0);
    timers.add(timer);
  }

  // One row: name | size | state and what the model is for | Download, Stop or Remove.
  function modelRow(m, error) {
    const act = async (method, path) => {
      try { await api(path, { method }); } catch (e) { alert(e.message); }
      await loadInfo().catch(() => {});
      load();
    };
    const line = h("span", { class: "settings-hint" });
    const bar = h("progress", { max: "1", value: "0", hidden: !m.job });
    let status = null, button = null;
    if (m.kind === "builtin") {
      status = m.state === "auto" ? h("span", { class: "settings-hint" }, t("w.mod.auto")) : ready();
    } else if (!m.available) {
      status = h("span", { class: "settings-hint" }, t(`w.dl.unavailable.${m.id}`));
    } else if (m.job) {
      status = line;
      button = h("button", { type: "button", class: "btn", onclick: () => act("POST", `/api/jobs/${m.job}/cancel`) }, t("w.dl.stop"));
    } else if (m.state === "installed") {
      status = ready();
      button = h("button", { type: "button", class: "btn", onclick: async () => {
        if (await confirmAlert({ title: t("w.dl.remove_confirm", { name: m.name }), keep: t("w.cancel"), confirm: t("w.dl.remove") }))
          act("DELETE", `/api/packs/${m.id}`);
      } }, t("w.dl.remove"));
    } else {
      status = h("span", { class: "settings-hint" }, t(m.state === "partial" ? "w.dl.state.partial" : "w.dl.state.absent"));
      button = h("button", { type: "button", class: "btn primary", onclick: () => act("POST", `/api/packs/${m.id}/install`) },
        m.state === "partial" ? t("w.dl.resume") : t("w.mod.download"));
    }
    const el = h("div", { class: `model-row ${m.job ? "running" : m.state}`, id: `model-${m.id}` },
      h("span", { class: "model-name" }, m.name),
      h("span", { class: "model-size" }, m.kind === "pack" && m.state !== "installed" ? gb(m.download_mb * 1e6) : gb(m.bytes)),
      h("div", { class: "model-state" }, status, h("span", { class: "settings-hint" }, t(`w.mod.note.${m.id}`)), bar,
        error ? h("span", { class: "error small" }, error) : null),
      button || h("span", {}));
    if (m.job) follow(m, bar, line);
    return el;
  }
  load();
}

// ---------- Storage ----------
// What DubEval keeps on this computer, in the Models list's shape: the evaluations, the downloaded videos (those no
// evaluation or draft uses can be cleared), the models, and the folder it all lives in.
function storageTab(panel, alive) {
  const draw = s => {
    if (!alive()) return;
    const total = s.evaluations.bytes + s.downloads.bytes + s.models_bytes;
    const open = h("button", { type: "button", class: "btn", onclick: () => api("/api/settings/open-data", { method: "POST" })
      .catch(e => alert(e.message)) }, t("w.priv.open"));
    const clear = h("button", { type: "button", class: "btn", disabled: !s.downloads.unused_bytes, onclick: async () => {
      if (!await confirmAlert({ title: t("w.store.clear_confirm", { size: gb(s.downloads.unused_bytes) }),
        text: t("w.store.clear_text"), keep: t("w.cancel"), confirm: t("w.store.clear") })) return;
      try { draw(await api("/api/settings/storage/clear", { method: "POST" })); } catch (e) { alert(e.message); }
    } }, t("w.store.clear"));
    const item = (name, size, note, button) => h("div", { class: "model-row" }, h("span", { class: "model-name" }, name),
      h("span", { class: "model-size" }, size), h("div", { class: "model-state" }, h("span", { class: "settings-hint" }, note)),
      button || h("span", {}));
    fill(panel,
      h("div", { class: "set-summary" }, t("w.store.summary", { size: gb(total) })),
      band(t("w.store.group.data"), gb(s.evaluations.bytes + s.downloads.bytes)),
      h("div", { class: "model-rows" },
        item(t("w.store.evaluations"), gb(s.evaluations.bytes), t("w.store.evaluations_note", { n: s.evaluations.count })),
        item(t("w.store.downloads"), gb(s.downloads.bytes), s.downloads.unused_bytes
          ? t("w.store.downloads_note", { size: gb(s.downloads.unused_bytes) }) : t("w.store.downloads_used"), clear)),
      band(t("w.store.group.models"), gb(s.models_bytes)),
      h("div", { class: "model-rows" },
        item(t("w.set.tab.models"), gb(s.models_bytes), t("w.store.models_note"),
          h("a", { class: "btn", href: "#/settings/models" }, t("w.store.manage")))),
      band(t("w.store.group.folder"), ""),
      h("div", { class: "model-rows" },
        h("div", { class: "model-row folder" }, h("span", { class: "mono" }, s.data_dir), open),
        h("p", { class: "settings-hint folder-note" }, t("w.priv.data_text"))));
  };
  api("/api/settings/storage").then(draw).catch(e => alive() && fill(panel, h("p", { class: "error" }, e.message)));
}

// ---------- API keys ----------
function keysTab(panel, view, show) {
  const j = view.judge;
  const judgeName = id => t(`w.set.judge.${id}`, { model: j.local_model });
  const showKeys = h("input", { type: "checkbox", class: "switch", "aria-label": t("w.set.show_keys") });
  const inputs = [];
  const rows = PROVIDERS.map(p => {
    const k = view.keys[p.id];
    const input = h("input", { type: "password", autocomplete: "off", spellcheck: "false", class: "path",
      placeholder: k.saved_here ? t("w.set.saved_placeholder") : k.set ? t("w.set.elsewhere") : t("w.set.not_set"),
      "aria-label": t(`w.set.${p.id}.title`) });
    input.value = pending.keys[p.id] || "";               // what was typed before switching tabs
    input.addEventListener("input", () => { pending.keys[p.id] = input.value; changed(); });
    inputs.push(input);
    const remove = k.saved_here ? h("button", { type: "button", class: "btn", onclick: async () => {
      if (await confirmAlert({ title: t("w.set.remove_confirm", { name: t(`w.set.${p.id}.title`) }), keep: t("w.cancel"),
        confirm: t("w.dl.remove") })) show(await api(`/api/settings/keys/${p.id}`, { method: "DELETE" }));
    } }, t("w.dl.remove")) : null;
    return row(t(`w.set.${p.id}.title`),
      h("div", { class: "set-inline" }, input, remove),
      h("span", { class: "settings-hint" }, t(`w.set.${p.id}.text`), " ",
        h("a", { href: p.link, target: "_blank", rel: "noopener", class: "settings-link" }, t("w.set.get_key"))),
      k.set && !k.saved_here ? h("span", { class: "settings-hint" }, t("w.set.elsewhere_note")) : null);
  });
  showKeys.addEventListener("change", () => inputs.forEach(i => { i.type = showKeys.checked ? "text" : "password"; }));
  fill(panel,
    row(t("w.set.checker"),
      h("strong", {}, j.active ? judgeName(j.active) : t("w.set.judge.none")),
      h("span", { class: "settings-hint" }, j.choice === "auto" ? t("w.set.auto") : t("w.set.forced", { name: j.choice })),
      h("ul", { class: "judges" }, j.order.map(id => h("li", {},
        h("span", { class: `badge ${j.available.includes(id) ? "good" : "info"}` },
          j.available.includes(id) ? t("w.set.ready") : t("w.set.not_ready")), " ", judgeName(id))))),
    rows,
    row(t("w.set.show_keys"), showKeys, h("span", { class: "settings-hint" }, t("w.set.show_keys_hint"))));
}

// ---------- Privacy ----------
function privacyTab(panel, view) {
  const j = view.judge;
  const checker = j.active ? t(`w.set.judge.${j.active}`, { model: j.local_model }) : t("w.set.judge.none");
  fill(panel,
    row(t("w.priv.usage"), h("span", {}, t("w.priv.usage_text"))),
    row(t("w.priv.translation"), h("span", {}, t("w.priv.translation_text", { checker }))),
    row(t("w.priv.links"), h("span", {}, t("w.priv.links_text"))),
    row(t("w.priv.downloads"), h("span", {}, t("w.priv.downloads_text"))),
    row(t("w.priv.data"), h("span", {}, t("w.priv.data_text")),
      h("a", { class: "settings-link", href: "#/settings/storage" }, t("w.store.see"))));
}

// ---------- About ----------
function aboutTab(panel, view) {
  const lang = h("select", {}, Object.entries(state.info.languages).map(([code, name]) =>
    h("option", { value: code, selected: code === (pending.lang || state.lang) }, name)));
  lang.addEventListener("change", () => { pending.lang = lang.value; changed(); });
  const list = h("ul", { class: "license-list", hidden: true },
    LICENSES.map(([name, license]) => h("li", {}, h("span", {}, name), h("span", { class: "muted" }, license))));
  const toggle = h("button", { type: "button", class: "link", "aria-expanded": "false", onclick: () => {
    list.hidden = !list.hidden;
    toggle.setAttribute("aria-expanded", String(!list.hidden));
  } }, t("w.about.ack"));
  fill(panel,
    row(t("w.about.version"), h("strong", {}, `DubEval ${view.version}`)),
    row(t("w.about.language"), lang),
    row(t("w.about.license"), h("span", {}, "AGPL-3.0-or-later"), h("span", { class: "settings-hint" }, t("w.about.license_text"))),
    row(t("w.about.copyright"), h("span", {}, "© 2026 ESTsoft corp.")),
    row(t("w.about.updates"), ...updatesControl()),
    h("div", { class: "set-row" }, h("span", {}, t("w.about.open_source")), h("div", { class: "set-ctl" }, toggle),
      h("div", { class: "set-wide" }, list, h("span", { class: "settings-hint" }, t("w.about.notice")))));
}

// About → Updates: a "Check for updates" button and what the check found (desktop app only).
function updatesControl() {
  if (!updatesAvailable()) return [h("span", { class: "settings-hint" }, t("w.upd.desktop_only"))];
  const status = h("span", { class: "settings-hint" }, t("w.upd.auto"));
  const button = h("button", { type: "button", class: "btn", onclick: () => checkForUpdates() }, t("w.upd.check"));
  watchUpdatesFor(button, u => {
    button.disabled = u.phase === "checking" || u.phase === "downloading";
    status.textContent = {
      checking: t("w.upd.checking"), none: t("w.upd.latest"), error: t("w.upd.failed"),
      downloading: t("w.upd.downloading", { pct: Math.round(u.pct || 0) }),
      ready: t("w.nav.update_ready", { version: u.version }),
    }[u.phase] || t("w.upd.auto");
  });
  return [button, status];
}

export function renderSettings(root, tab) {
  let alive = true;
  const timers = new Set();
  const current = TABS.includes(tab) ? tab : "models";
  const list = ["models", "storage"].includes(current);      // bands over rows, edge to edge
  const panel = h("div", { class: `set-panel${list ? " list" : ""}`, role: "tabpanel" }, h("p", { class: "muted" }, t("w.loading")));
  const tabs = h("div", { class: "set-tabs", role: "tablist", "aria-label": t("w.set.title") },
    TABS.map(id => h("button", { type: "button", role: "tab", class: "set-tab", "aria-selected": String(id === current),
      onclick: () => { location.hash = `#/settings/${id}`; } }, t(`w.set.tab.${id}`))));
  root.append(tabs, panel);                         // inside the Settings dialog, which has the title

  const show = view => {
    if (!alive) return;
    loadInfo().catch(() => {});
    if (current === "keys") keysTab(panel, view, show);
    else if (current === "privacy") privacyTab(panel, view);
    else if (current === "about") aboutTab(panel, view);
  };
  if (current === "models") modelsTab(panel, timers, () => alive);
  else if (current === "storage") storageTab(panel, () => alive);
  else api("/api/settings").then(show).catch(e => alive && fill(panel, h("p", { class: "error" }, e.message)));
  return () => { alive = false; for (const timer of timers) clearTimeout(timer); };
}
