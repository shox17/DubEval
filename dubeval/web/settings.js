// Settings, laid out like PersoDub's: one row of tabs (Models, API keys, Privacy, About), then one darker panel of
// "label | control" rows. Keys are written once and never shown back; models download with progress, stop and resume.
import { api, fill, h, loadInfo, setLanguage, state, t } from "./app.js";
import { checkForUpdates, updatesAvailable, watchUpdatesFor } from "./shell.js";

const TABS = ["models", "keys", "privacy", "about"];
const POLL_MS = 1000;
const PROVIDERS = [
  { id: "anthropic", judge: "claude", link: "https://console.anthropic.com/settings/keys" },
  { id: "gemini", judge: "gemini", link: "https://aistudio.google.com/apikey" },
  { id: "openai", judge: "openai", link: "https://platform.openai.com/api-keys" },
];
const LICENSES = [
  ["faster-whisper / CTranslate2", "MIT"], ["Whisper models", "MIT"], ["BGE-M3", "MIT"],
  ["WeSpeaker ResNet34", "CC BY 4.0"], ["DNSMOS P.835", "CC BY 4.0"], ["MediaPipe Face Landmarker", "Apache-2.0"],
  ["librosa", "ISC"], ["onnxruntime", "MIT"], ["FFmpeg", "LGPL / GPL"], ["Onest typeface", "OFL-1.1"],
  ["Electron", "MIT"], ["PersoDub (design, icon)", "AGPL-3.0 / ESTsoft"],
];

const gb = bytes => (bytes == null ? "—" : bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB`
  : `${Math.max(1, Math.round(bytes / 1e6))} MB`);
const row = (label, ...control) => h("div", { class: "set-row" }, h("span", {}, label),
  h("div", { class: "set-ctl" }, ...control));

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
      out.push(h("div", { class: "model-group-head" }, h("span", {}, t(`w.mod.group.${group.id}`)),
        h("span", { class: "model-size" }, total ? gb(total) : "")));
      for (const m of group.rows) out.push(modelRow(m, errors[m.id]));
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

  function modelRow(m, error) {
    const act = async (method, path) => {
      try { await api(path, { method }); } catch (e) { alert(e.message); }
      await loadInfo().catch(() => {});
      load();
    };
    const status = m.job ? "running" : m.state;
    const line = h("span", { class: "settings-hint" });
    const bar = h("progress", { max: "1", value: "0", hidden: !m.job });
    let button = null;
    if (m.kind === "builtin") {
      line.textContent = t(status === "auto" ? "w.mod.auto" : "w.mod.builtin");
    } else if (!m.available) {
      line.textContent = t(`w.dl.unavailable.${m.id}`);
    } else if (m.job) {
      button = h("button", { type: "button", class: "btn", onclick: () => act("POST", `/api/jobs/${m.job}/cancel`) }, t("w.dl.stop"));
    } else if (m.state === "installed") {
      line.textContent = t("w.mod.ready");
      button = h("button", { type: "button", class: "btn", onclick: () => {
        if (confirm(t("w.dl.remove_confirm", { name: m.name }))) act("DELETE", `/api/packs/${m.id}`);
      } }, t("w.dl.remove"));
    } else {
      if (m.state === "partial") line.textContent = t("w.dl.state.partial");
      button = h("button", { type: "button", class: "btn primary", onclick: () => act("POST", `/api/packs/${m.id}/install`) },
        m.state === "partial" ? t("w.dl.resume") : t("w.mod.download"));
    }
    const el = h("div", { class: `model-row ${status}`, id: `model-${m.id}` },
      h("div", { class: "model-main" }, h("span", { class: "model-name" }, m.name),
        h("span", { class: "model-note" }, t(`w.mod.note.${m.id}`)), line, bar,
        error ? h("span", { class: "error small" }, error) : null),
      h("span", { class: "model-size" }, m.kind === "pack" && m.state !== "installed" ? gb(m.download_mb * 1e6) : gb(m.bytes)),
      button || h("span", {}));
    if (m.job) follow(m, bar, line);
    return el;
  }
  load();
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
    inputs.push(input);
    const error = h("span", { class: "error small" });
    const save = h("button", { type: "button", class: "btn primary", onclick: async () => {
      error.textContent = "";
      try {
        const next = await api(`/api/settings/keys/${p.id}`, { method: "PUT", body: JSON.stringify({ key: input.value }) });
        input.value = "";
        show(next);
      } catch (e) { error.textContent = e.message; }
    } }, k.saved_here ? t("w.set.replace") : t("w.set.save"));
    const remove = k.saved_here ? h("button", { type: "button", class: "btn", onclick: async () => {
      if (confirm(t("w.set.remove_confirm", { name: t(`w.set.${p.id}.title`) })))
        show(await api(`/api/settings/keys/${p.id}`, { method: "DELETE" }));
    } }, t("w.dl.remove")) : null;
    return row(t(`w.set.${p.id}.title`),
      h("div", { class: "set-inline" }, input, save, remove),
      h("span", { class: "settings-hint" }, t(`w.set.${p.id}.text`), " ",
        h("a", { href: p.link, target: "_blank", rel: "noopener", class: "settings-link" }, t("w.set.get_key"))),
      k.set && !k.saved_here ? h("span", { class: "settings-hint" }, t("w.set.elsewhere_note")) : null, error);
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
    row(t("w.priv.data"),
      h("span", { class: "mono" }, view.data_dir),
      h("span", { class: "settings-hint" }, t("w.priv.data_text")),
      h("button", { type: "button", class: "btn", onclick: () => api("/api/settings/open-data", { method: "POST" })
        .catch(e => alert(e.message)) }, t("w.priv.open"))));
}

// ---------- About ----------
function aboutTab(panel, view) {
  const lang = h("select", {}, Object.entries(state.info.languages).map(([code, name]) =>
    h("option", { value: code, selected: code === state.lang }, name)));
  lang.addEventListener("change", () => setLanguage(lang.value));
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
  const panel = h("div", { class: "set-panel", role: "tabpanel" }, h("p", { class: "muted" }, t("w.loading")));
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
  else api("/api/settings").then(show).catch(e => alive && fill(panel, h("p", { class: "error" }, e.message)));
  return () => { alive = false; for (const timer of timers) clearTimeout(timer); };
}
