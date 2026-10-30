// Start screen: the original and its dub (a file, a path on this computer or a link), then a few options.
// Once a video is given, the page keeps itself as a draft on the server (its card is on the home screen) and saves as
// it is edited; #/draft/<id> fills it in again. A chosen file is added (uploaded) as soon as it is chosen, so the
// draft holds it too.
import { INFO_EVENT, api, fmtTime, go, h, setAddress, state, t } from "./app.js";
import { PREFILL_KEY } from "./home.js";

const SHARE_LINK = /^https?:\/\/(www\.)?perso\.ai\//i;
const SAVE_WAIT_MS = 700;                  // after the last change, before the draft is saved

// Uploads a chosen file with progress; resolves to "upload:<id>".
function upload(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    xhr.open("POST", "/api/uploads");
    xhr.setRequestHeader("Accept-Language", state.lang);
    xhr.upload.onprogress = e => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      xhr.status < 300 ? resolve(data.id) : reject(new Error(data.detail || xhr.statusText));
    };
    xhr.onerror = () => reject(new Error(t("w.err.upload")));
    xhr.send(form);
  });
}

const PREVIEW_WAIT_MS = 600;               // after the last keystroke, before a typed link or path is read
const LINK_POLL_MS = 700;                  // how often a link being downloaded is asked how far it is

// Downloads a pasted link on the server (any kind: a video page, a file, a file host's share); resolves to
// {id: "upload:<id>", name} like an upload. onProgress hears a fraction, or null while the size is unknown.
async function downloadLink(url, onProgress, stillWanted) {
  const { id } = await api("/api/uploads/link", { method: "POST", body: JSON.stringify({ url }) });
  for (;;) {
    await new Promise(r => setTimeout(r, LINK_POLL_MS));
    if (!stillWanted()) return null;
    const s = await api(`/api/uploads/link/${id}`);
    if (s.state === "done") return { id: s.upload, name: s.name };
    if (s.state === "failed") throw new Error(s.error);
    onProgress(s.progress);
  }
}

// The preview under an input: a picture (or the chosen file itself), its title and one line about it.
function previewBox() {
  const el = h("div", { class: "preview", hidden: true });
  let objectUrl = null;
  const release = () => { if (objectUrl) URL.revokeObjectURL(objectUrl); objectUrl = null; };
  return {
    el,
    clear() { release(); el.hidden = true; el.replaceChildren(); },
    busy() { release(); el.hidden = false; el.replaceChildren(h("span", { class: "muted small" }, t("w.prev.reading"))); },
    error(message) { release(); el.hidden = false; el.replaceChildren(h("span", { class: "error small" }, message)); },
    file(file) {
      release();
      objectUrl = URL.createObjectURL(file);
      el.hidden = false;
      el.replaceChildren(h("video", { class: "thumb", src: objectUrl, muted: true, preload: "metadata", controls: true }),
        h("div", { class: "preview-text" }, h("strong", {}, file.name),
          h("span", { class: "muted small" }, `${t("w.prev.on_computer")} · ${(file.size / 1048576).toFixed(1)} MB`)));
    },
    show(p, title = null, note = null) {
      release();
      const meta = [p.kind === "file" ? t("w.prev.on_computer") : p.site, p.duration_sec ? fmtTime(p.duration_sec) : null,
        p.source_lang && p.target_lang ? `${langName(p.source_lang)} → ${langName(p.target_lang)}` : null,
        p.lipsync ? t("w.prev.lipsync") : null].filter(Boolean).join(" · ");
      el.hidden = false;
      el.replaceChildren(p.thumbnail ? h("img", { class: "thumb", src: p.thumbnail, alt: "" }) : h("div", { class: "thumb" }),
        h("div", { class: "preview-text" }, h("strong", {}, title || p.title || "–"),
          meta ? h("span", { class: "muted small" }, meta) : null,
          note ? h("span", { class: "muted small" }, note) : null));
    },
  };
}

// A language's name in the page's language ("uz" → "Uzbek", "우즈베크어", ...).
function langName(code) {
  try { return new Intl.DisplayNames([state.lang], { type: "language" }).of(code) || code; } catch { return code; }
}

// A file field's state: a file being added (uploaded) or added, else what was typed. onChange hears every change.
function fileState(onChange) {
  let uploaded = null;                  // {id: "upload:<id>", name} once the server has the file
  let pending = null;                   // the upload in progress
  return {
    get uploaded() { return uploaded; },
    get pending() { return pending; },
    // Adds a chosen file; bar shows the progress. Resolves to the upload, or null when it failed or was replaced.
    add(file, bar, error) {
      uploaded = null;
      bar.hidden = false;
      bar.value = 0;
      error.textContent = "";
      const mine = pending = upload(file, f => { bar.value = f; }).then(id => {
        if (pending !== mine) return null;
        uploaded = { id, name: file.name };
        return uploaded;
      }).catch(e => {
        if (pending === mine) error.textContent = e.message;
        return null;
      }).finally(() => {
        if (pending === mine) { pending = null; bar.hidden = true; onChange(); }
      });
      return mine;
    },
    // Downloads a pasted link the same way: the card then holds the downloaded video like a chosen file.
    addLink(url, bar, error) {
      uploaded = null;
      bar.hidden = false;
      bar.removeAttribute("value");                   // moving until the size is known
      error.textContent = "";
      let mine = null;
      mine = pending = downloadLink(url, f => { if (f != null) bar.value = f; }, () => pending === mine).then(got => {
        if (!got || pending !== mine) return null;
        uploaded = got;
        return uploaded;
      }).catch(e => {
        if (pending === mine) error.textContent = e.message;
        return null;
      }).finally(() => {
        if (pending === mine) { pending = null; bar.hidden = true; bar.value = 0; onChange(); }
      });
      return mine;
    },
    set(saved) { pending = null; uploaded = saved && saved.id ? { id: saved.id, name: saved.name || "" } : null; },
    clear() { pending = null; uploaded = null; },
  };
}

// One input card: drop or choose a file, or type a path or link; what was given is previewed under it.
// value() gives what the server needs; onPreview(fn) hears each preview read from a typed link or path.
function source(kind, title, hint, accept, onChange, onRemove = null, placeholder = t("w.start.path")) {
  let chosen = null;                    // a File picked or dropped (shown from memory while it is being added)
  let included = false;                 // the original comes with a Perso share link: nothing to give here
  let listener = () => {}, timer = null, asked = "", last = null;
  let fetching = null;                  // the link being downloaded into this card, if any
  const files = fileState(onChange);
  const text = h("input", { type: "text", class: "path", placeholder, title: placeholder, "aria-label": title });
  const fileInput = h("input", { type: "file", accept, class: "sr", tabindex: "-1" });
  const name = h("span", { class: "chosen muted" });
  const bar = h("progress", { max: "1", value: "0", hidden: true, "aria-label": t("w.start.uploading") });
  const error = h("span", { class: "error small" });
  const box = previewBox();
  const pickRow = h("div", { class: "drop-row" });
  const fileName = () => (chosen ? chosen.name : files.uploaded ? files.uploaded.name : "");
  const show = () => {
    name.textContent = fileName();
    text.hidden = !!fileName();
    clear.hidden = !fileName();
    pickRow.hidden = included;
  };
  const clear = h("button", { type: "button", class: "link", hidden: true, onclick: () => {
    chosen = null; files.clear(); fileInput.value = ""; last = null; error.textContent = ""; bar.hidden = true;
    show(); box.clear(); read(); onChange();
  } }, t("w.start.clear"));
  // A file is added at once; its picture comes from the server (the draft keeps it for the home screen's card).
  async function choose(file) {
    cancelLink();
    chosen = file;
    text.value = "";
    asked = "";
    show();
    box.file(file);
    listener(null, "");                   // a file, not a share link: an original that came with one is let go
    onChange();
    const added = await files.add(file, bar, error);
    if (!added) return;
    try { last = await api(`/api/preview?source=${encodeURIComponent(added.id)}`); } catch { last = null; }
    onChange();
  }
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) choose(fileInput.files[0]); });
  // A pasted link (not a Perso share link, which brings its own original) is downloaded at once, whatever kind
  // it is: the card then holds the video like a chosen file. Even a link that couldn't be previewed is tried.
  async function fetchLink(value, p) {
    error.textContent = "";
    name.textContent = t("w.start.downloading");
    fetching = value;
    const got = await files.addLink(value, bar, error);
    if (fetching === value) fetching = null;
    if (!got || asked !== value) { name.textContent = fileName(); return; }
    if (p?.title) got.name = p.title;                 // the video's title, not the downloaded file's stored name
    text.value = "";
    asked = "";
    show();
    try { last = await api(`/api/preview?source=${encodeURIComponent(got.id)}`); } catch { last = p; }
    if (last) box.show(last, p?.title || got.name, t("w.start.downloaded"));
    onChange();
  }
  // A link still downloading when the card is given something else: its video must not land in the card later.
  function cancelLink() {
    if (fetching === null) return;
    fetching = null;
    files.clear();
    bar.hidden = true;
    bar.value = 0;
    name.textContent = fileName();
  }
  // A typed link or path is read once typing stops; only the latest answer is shown.
  async function read() {
    const value = text.value.trim();
    if (value === asked) return;
    asked = value;
    if (fetching !== null && fetching !== value) cancelLink();
    if (!value) { box.clear(); last = null; listener(null, ""); return; }
    box.busy();
    let p = null;
    try {
      p = await api(`/api/preview?source=${encodeURIComponent(value)}`);
      if (asked !== value) return;
      last = p;
      box.show(p);
      listener(p, value);
    } catch (e) {
      if (asked !== value) return;
      last = null;
      if (!/^https?:\/\//i.test(value)) box.error(e.message);
      listener(null, value);
    }
    onChange();
    if (/^https?:\/\//i.test(value) && !(p && p.kind === "perso")) fetchLink(value, p);
  }
  text.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(read, PREVIEW_WAIT_MS); });
  text.addEventListener("paste", () => { clearTimeout(timer); timer = setTimeout(read, 50); });
  const heading = h("strong", {}, title);
  const card = h("div", { class: `drop ${kind}` },
    h("div", { class: "drop-head" }, h("div", { class: "row" }, heading, h("span", { class: "grow" }),
      onRemove ? h("button", { type: "button", class: "link", onclick: onRemove }, t("w.start.clear")) : null),
      h("span", { class: "muted" }, hint)),
    pickRow,
    box.el, bar, error, fileInput);
  pickRow.append(h("button", { type: "button", onclick: () => fileInput.click() }, t("w.start.choose")),
    h("span", { class: "muted or" }, t("w.start.or")), text, name, clear);
  card.addEventListener("dragover", e => { e.preventDefault(); card.classList.add("over"); });
  card.addEventListener("dragleave", () => card.classList.remove("over"));
  card.addEventListener("drop", e => {
    e.preventDefault();
    card.classList.remove("over");
    if (e.dataTransfer.files[0]) choose(e.dataTransfer.files[0]);
  });
  return {
    card,
    setTitle(title) { heading.textContent = title; text.setAttribute("aria-label", title); },
    typed: () => (fileName() ? "" : text.value.trim()),
    empty: () => !fileName() && !text.value.trim() && !included,
    onPreview(fn) { listener = fn; },
    preview: () => last,
    setTyped(value) { cancelLink(); chosen = null; files.clear(); fileInput.value = ""; text.value = value; show(); read(); },
    // The original that comes with a Perso share link: shown, nothing to give (p: that link's preview, or null).
    include(p) {
      included = !!p;
      if (p) { chosen = null; files.clear(); text.value = ""; asked = ""; box.show(p, t("w.prev.from_share"), t("w.prev.included")); }
      else box.clear();
      show();
    },
    // What the draft keeps: the added file (id and name) or the typed text.
    state: () => (files.uploaded ? { upload: files.uploaded.id, name: files.uploaded.name } : { typed: text.value.trim() }),
    async restore(saved) {
      if (!saved) return;
      if (saved.upload) {
        files.set({ id: saved.upload, name: saved.name });
        show();
        box.busy();
        try {
          last = await api(`/api/preview?source=${encodeURIComponent(saved.upload)}`);
          box.show(last, saved.name);
        } catch (e) {
          box.error(e.message);       // kept: starting says plainly if the file is gone ("choose it again")
        }
      } else if (saved.typed) {
        text.value = saved.typed;
        show();
        await read();
      }
    },
    async value() {
      if (files.pending) await files.pending;
      if (files.uploaded) return files.uploaded.id;
      if (fileName()) throw new Error(error.textContent || t("w.err.upload"));   // the file couldn't be added
      return text.value.trim() || null;
    },
  };
}

// A language picker: "Detect automatically", then every language speech recognition knows, named in the page's
// language (the browser knows the names; the server's English name is the fallback) and sorted by that name.
function languageSelect(id = null) {
  let names = null;
  try { names = new Intl.DisplayNames([state.lang], { type: "language" }); } catch { /* English names */ }
  const named = Object.entries(state.info.speech_languages).map(([code, english]) => {
    let name = null;
    try { name = names && names.of(code); } catch { /* a code the browser doesn't know */ }
    return [code, name && name !== code ? name : english];
  }).sort((a, b) => a[1].localeCompare(b[1], state.lang));
  return h("select", { id, class: "lang-pick" }, h("option", { value: "" }, t("w.start.lang_auto")),
    named.map(([code, name]) => h("option", { value: code }, `${name} (${code})`)));
}

// Picks a value in a select when it is one of its (enabled) options.
function pick(select, value) {
  if ([...select.options].some(o => o.value === value && !o.disabled)) select.value = value;
}

// "?" next to the kind of dub: every kind and what it changes, on hover or keyboard focus.
function typeHelp(dubTypes) {
  return h("span", { class: "tip", tabindex: "0", role: "note", "aria-label": t("w.start.type_help") }, "?",
    h("span", { class: "tip-body", role: "tooltip" }, ["unknown", ...dubTypes].map(k =>
      h("span", { class: "tip-row" }, h("strong", {}, t(`w.type.${k}`)), t(`w.type.${k}_hint`)))));
}

// An optional subtitle file inside a video card: choose or drop it, or type its path. value() gives what the server
// needs (a chosen file is added at once, like a video).
function subtitleField(onChange) {
  let chosen = null;
  const files = fileState(onChange);
  const fileInput = h("input", { type: "file", accept: ".srt,.vtt", class: "sr", tabindex: "-1" });
  const text = h("input", { type: "text", class: "path", placeholder: t("w.start.path"), "aria-label": t("w.start.subs") });
  const name = h("span", { class: "chosen muted" });
  const bar = h("progress", { max: "1", value: "0", hidden: true, "aria-label": t("w.start.uploading") });
  const error = h("span", { class: "error small" });
  const fileName = () => (chosen ? chosen.name : files.uploaded ? files.uploaded.name : "");
  const clear = h("button", { type: "button", class: "link", hidden: true,
    onclick: () => { chosen = null; files.clear(); fileInput.value = ""; error.textContent = ""; show(); onChange(); } },
    t("w.start.clear"));
  const show = () => { name.textContent = fileName(); text.hidden = !!fileName(); clear.hidden = !fileName(); };
  const choose = file => { chosen = file; show(); onChange(); files.add(file, bar, error); };
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) choose(fileInput.files[0]); });
  const el = h("div", { class: "subs-field" },
    h("span", { class: "subs-label" }, t("w.start.subs"), h("span", { class: "muted small" }, ` · ${t("w.start.optional")}`)),
    h("div", { class: "drop-row" }, h("button", { type: "button", onclick: () => fileInput.click() }, t("w.start.choose")),
      h("span", { class: "muted or" }, t("w.start.or")), text, name, clear), bar, error, fileInput);
  el.addEventListener("dragover", e => { e.preventDefault(); });
  el.addEventListener("drop", e => {
    e.preventDefault();
    e.stopPropagation();                            // the subtitle file, not the card's video
    el.closest(".drop")?.classList.remove("over");  // so the card's own drop handler, which clears this, doesn't run
    if (e.dataTransfer.files[0]) choose(e.dataTransfer.files[0]);
  });
  return {
    el,
    state: () => (files.uploaded ? { upload: files.uploaded.id, name: files.uploaded.name } : { typed: text.value.trim() }),
    restore(saved) {
      if (saved && saved.upload) files.set({ id: saved.upload, name: saved.name });
      else if (saved && saved.typed) text.value = saved.typed;
      show();
    },
    async value() {
      if (files.pending) await files.pending;
      if (files.uploaded) return files.uploaded.id;
      if (fileName()) throw new Error(error.textContent || t("w.err.upload"));
      return text.value.trim() || null;
    },
  };
}

// Adds the dub's kind and language under a dub card; d.settings() gives them for the request.
function withSettings(d, dubTypes, onChange) {
  const kinds = ["", ...dubTypes];
  const hintOf = k => t(`w.type.${k || "unknown"}_hint`);
  const type = h("select", {}, kinds.map(k => h("option", { value: k, title: hintOf(k) }, t(`w.type.${k || "unknown"}`))));
  const meaning = h("span", { class: "type-hint muted small" });
  const explain = () => { meaning.textContent = hintOf(type.value); type.title = hintOf(type.value); };
  type.addEventListener("change", explain);
  explain();
  const lang = languageSelect();
  const subtitles = subtitleField(onChange);
  d.card.append(h("div", { class: "dub-settings" },
    h("label", {}, h("span", { class: "row" }, t("w.start.dub_type"), typeHelp(dubTypes)), type),
    h("label", {}, t("w.start.target_lang"), lang), meaning), subtitles.el);
  d.settings = async () => ({ dub_type: type.value || null, target_lang: lang.value || null,
    subtitles: await subtitles.value() });
  d.setLanguage = code => pick(lang, code);
  const sourceState = d.state, sourceRestore = d.restore;
  d.state = () => ({ ...sourceState(), dub_type: type.value, target_lang: lang.value, subtitles: subtitles.state() });
  d.restore = async saved => {
    if (!saved) return;
    pick(type, saved.dub_type || "");
    explain();
    pick(lang, saved.target_lang || "");
    subtitles.restore(saved.subtitles);
    await sourceRestore(saved);
  };
  return d;
}

// renderStart(root, {draftId}): a draft filled in again; {compare: true}: a new comparison (two dub cards).
export function renderStart(root, { draftId = null, compare = false } = {}) {
  const info = state.info;
  let left = false, draft = draftId, saveTimer = null, saving = Promise.resolve(), submitted = false, restoring = true;
  const changed = () => {
    if (restoring || submitted) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { saveTimer = null; saving = saving.then(saveDraft); }, SAVE_WAIT_MS);
  };
  const video = "video/*,audio/*,.mkv,.mov,.mp4,.webm,.wav,.mp3,.m4a";
  const original = source("original", t("w.start.original"), t("w.start.original_hint"), video, changed, null,
    t("w.start.link_hint"));
  const sourceLang = languageSelect("src-lang");
  const originalSubs = subtitleField(changed);
  original.card.append(h("div", { class: "dub-settings" }, h("label", {}, t("w.start.source_lang"), sourceLang)),
    originalSubs.el);
  const dub = withSettings(source("dub", t("w.start.dub"), t("w.start.dub_hint"), video, changed), info.dub_types, changed);
  const dubs = [dub];
  const dubList = h("div", { class: "dubs" }, dub.card);
  const LETTERS = "ABCDEFGH";
  function addDub() {
    const extra = withSettings(source("dub", "", t("w.start.dub_hint"), video, changed, () => {
      dubs.splice(dubs.indexOf(extra), 1);
      extra.card.remove();
      relabel();
      changed();
    }), info.dub_types, changed);
    dubs.push(extra);
    dubList.append(extra.card);
    relabel();
    return extra;
  }
  const addBtn = h("button", { type: "button", onclick: () => { addDub(); changed(); } }, t("w.start.add_dub"));

  // Automatic picks the large model on a GPU when it is downloaded (the server says which it would be).
  const speechModel = h("select", { id: "speech-model" },
    h("option", { value: "auto" }, t("w.start.model_auto", { model: t(info.speech_auto === "base"
      ? "w.start.model_standard" : "w.start.model_large") })),
    h("option", { value: "standard" }, t("w.start.model_standard")),
    h("option", { value: "large" }, t("w.start.model_large")));
  // Checks that won't run as things are set up, each with where to get what it needs.
  const missing = [
    !info.meaning_ready && ["w.start.need_meaning", "#/settings/models"],
  ].filter(Boolean);
  // A Perso share link (in either box) is the dub and brings its original and both languages: fill them in.
  const filled = h("p", { class: "muted small filled-note", hidden: true }, t("w.prev.filled"));
  let sharedOriginal = false;
  dub.onPreview(p => {
    const share = p && p.kind === "perso";
    if (share) {
      original.include(p);
      dub.setLanguage(p.target_lang);
      pick(sourceLang, p.source_lang);
    } else if (sharedOriginal) {
      original.include(null);
    }
    sharedOriginal = share;
    filled.hidden = !share;
  });
  original.onPreview((p, value) => {
    if (p && p.kind === "perso") dub.setTyped(value);       // the share link is the dub; its original comes with it
  });
  const checkers = [["claude", t("w.set.judge.claude")], ["gemini", t("w.set.judge.gemini")],
    ["openai", t("w.set.judge.openai")], ["ollama", t("w.start.judge_local")]];
  const ready = id => state.info.judges.includes(id);
  const label = (id, name) => (ready(id) ? name
    : t(id === "ollama" ? "w.start.judge_needs_local" : "w.start.judge_needs_key", { judge: name }));
  const firstReady = checkers.find(([id]) => ready(id));
  const check = h("select", { id: "check" },
    checkers.map(([id, name]) => h("option", { value: id, disabled: !ready(id), selected: firstReady?.[0] === id },
      label(id, name))),
    h("option", { value: "off", selected: !firstReady }, t("w.start.judge_off")));
  let checkChosen = false;                          // the person picked the checker (then a new key doesn't change it)
  check.addEventListener("change", () => { checkChosen = true; });
  // Settings changed what's set up (a key saved through "Add a key", the local model downloaded): the list follows,
  // and a page that had no checker picks the first one now ready.
  function refreshCheckers() {
    for (const option of check.options) {
      const entry = checkers.find(([id]) => id === option.value);
      if (!entry) continue;
      option.disabled = !ready(entry[0]);
      option.textContent = label(...entry);
    }
    const first = checkers.find(([id]) => ready(id));
    if (!checkChosen && check.value === "off" && first) check.value = first[0];
    if (check.selectedOptions[0]?.disabled) check.value = first ? first[0] : "off";
  }
  window.addEventListener(INFO_EVENT, refreshCheckers);
  const needKeys = checkers.some(([id]) => id !== "ollama" && !ready(id));
  const lipsync = h("input", { type: "checkbox", id: "lipsync" });
  const error = h("p", { class: "error", role: "alert" });
  const savedNote = h("p", { class: "muted small", hidden: true }, t("w.start.draft_saved"));
  const startBtn = h("button", { type: "submit", class: "primary" }, t("w.start.go"));
  // One dub: "Dubbed video"; several: "Dub A", "Dub B", ... and the comparison button.
  function relabel() {
    const many = dubs.length > 1;
    dubs.forEach((d, i) => d.setTitle(many ? t("w.start.dub_n", { d: LETTERS[i] }) : t("w.start.dub")));
    addBtn.hidden = dubs.length >= LETTERS.length;
    startBtn.textContent = many ? t("w.start.go_compare", { n: dubs.length }) : t("w.start.go");
  }
  const more = h("details", { class: "more" }, h("summary", {}, t("w.start.more")),
    h("div", { class: "options" },
      h("label", {}, t("w.start.translation"), check),
      needKeys ? h("a", { class: "fix-link", href: "#/settings/keys" }, t("w.start.judge_add")) : null,
      !ready("ollama") ? h("a", { class: "fix-link", href: "#/settings/models" }, t("w.start.get_local")) : null,
      missing.map(([key, href]) => h("a", { class: "fix-link", href }, t(key)))),
    h("div", { class: "options" },
      info.large_model ? h("label", {}, t("w.start.speech_model"), speechModel)
        : h("a", { href: "#/settings/models", class: "small" }, t("w.start.get_large")),
      h("label", { class: "check" }, lipsync, t(info.lip_sync ? "w.start.lip_sync" : "w.start.lipsync"))),
    h("p", { class: "muted small" }, t("w.start.lang_pick")));
  let restoredToggle = false;                        // the toggle that restoring "More options" fires, later
  more.addEventListener("toggle", () => { if (restoredToggle) restoredToggle = false; else changed(); });

  // ----- the draft -----
  const formState = () => ({ original: original.state(), original_subs: originalSubs.state(), source_lang: sourceLang.value,
    dubs: dubs.map(d => d.state()), judge: check.value, lipsync: lipsync.checked, speech_model: speechModel.value,
    more_open: more.open });
  const given = () => !original.empty() || dubs.some(d => !d.empty());
  // The card's name and picture: the first dub's (the chosen file's own name, or a link's title), else the original's.
  function cardFace() {
    const faces = [...dubs, original].map(s => ({ name: s.state().name || s.preview()?.title, thumbnail: s.preview()?.thumbnail }));
    const face = faces.find(f => f.name || f.thumbnail) || {};
    return { name: face.name || null, thumbnail: face.thumbnail || faces.find(f => f.thumbnail)?.thumbnail || null };
  }
  // Saves the draft (or deletes it when nothing is given). After the page was left it still saves a change that was
  // waiting, but no longer touches the page or its address.
  async function saveDraft() {
    if (submitted) return;
    try {
      if (!given()) {                       // everything was removed: so is the draft
        if (draft) {
          await api(`/api/drafts/${draft}`, { method: "DELETE" }).catch(() => {});
          draft = null;
          savedNote.hidden = true;
          if (!left) setAddress("#/new");
        }
        return;
      }
      const body = JSON.stringify({ ...cardFace(), form: formState() });
      const saved = draft ? await api(`/api/drafts/${draft}`, { method: "PUT", body })
        : await api("/api/drafts", { method: "POST", body });
      if (!draft && !left) setAddress(`#/draft/${saved.id}`);    // reopening this address continues the draft
      draft = saved.id;
      savedNote.hidden = false;
    } catch (e) {
      // A draft that was deleted elsewhere (or started) becomes a new one at the next change.
      if (e.status === 404) draft = null;
    }
  }

  async function restore() {
    if (draftId) {
      try {
        const d = await api(`/api/drafts/${encodeURIComponent(draftId)}`);
        if (d.job?.id) {
          const job = await api(`/api/jobs/${encodeURIComponent(d.job.id)}`).catch(() => null);
          if (job && job.status === "running") { go(`#/job/${d.job.id}`, { replace: true }); return; }
        }
        const f = d.form || {};
        await original.restore(f.original);
        originalSubs.restore(f.original_subs);
        pick(sourceLang, f.source_lang || "");
        for (let i = 1; i < (f.dubs || []).length; i++) addDub();
        await Promise.all((f.dubs || []).map((saved, i) => dubs[i].restore(saved)));
        pick(sourceLang, f.source_lang || "");    // a share link's preview may have set it: the saved choice wins
        pick(check, f.judge || "");
        lipsync.checked = !!f.lipsync;
        pick(speechModel, f.speech_model || "auto");
        if (more.open !== !!f.more_open) { restoredToggle = true; more.open = !!f.more_open; }
        savedNote.hidden = false;
      } catch (e) {
        draft = null;
        setAddress("#/new");
        error.textContent = e.message;
      }
    } else {
      if (compare) addDub();
      // What the home screen's card was given: a file it added (upload) or a link, for the dub's card.
      let given = null;
      try { given = sessionStorage.getItem(PREFILL_KEY); sessionStorage.removeItem(PREFILL_KEY); } catch { /* none */ }
      if (given) {
        let parsed = null;
        try { parsed = JSON.parse(given); } catch { parsed = { link: given }; }
        if (parsed.upload) await dub.restore({ upload: parsed.upload, name: parsed.name });
        else if (parsed.link) dub.setTyped(parsed.link);
        restoring = false;
        changed();
      }
    }
    restoring = false;
  }

  const form = h("form", { class: "start", novalidate: true, onsubmit: async e => {
    e.preventDefault();
    error.textContent = "";
    // Perso share links include their original, so the original may stay empty for them (the server checks again).
    const allShares = dubs.every(d => SHARE_LINK.test(d.typed()));
    if ((original.empty() && !allShares) || dubs.some(d => d.empty())) { error.textContent = t("w.err.both"); return; }
    startBtn.disabled = true;
    try {
      clearTimeout(saveTimer);
      await saving;
      await saveDraft();                    // the draft's card follows the evaluation, so it must exist first
      const values = [];
      for (const d of dubs) values.push(await d.value());
      const body = { original: await original.value(), dub: values[0], more_dubs: values.slice(1),
        original_subtitles: await originalSubs.value(),
        source_lang: sourceLang.value || null, dub_options: await Promise.all(dubs.map(d => d.settings())),
        speech_model: info.large_model ? speechModel.value : "auto",
        translation_check: check.value !== "off", judge: check.value, lipsync: lipsync.checked,
        lang: state.lang, draft_id: draft };
      submitted = true;
      const job = await api("/api/evaluations", { method: "POST", body: JSON.stringify(body) });
      go(`#/job/${job.id}`);
    } catch (err) {
      submitted = false;
      error.textContent = err.message;
      startBtn.disabled = false;
    }
  } },
    h("h1", {}, t("w.start.title")),
    h("p", { class: "muted lead" }, t("w.start.lead")),
    h("div", { class: "pair" }, original.card, h("div", {}, dubList, h("div", { class: "add" }, addBtn))),
    filled,
    more,
    error,
    h("div", { class: "actions" }, savedNote, h("span", { class: "grow" }), startBtn));
  form.addEventListener("input", changed);
  form.addEventListener("change", changed);
  relabel();
  root.append(form);
  restore();
  return () => {
    left = true;
    window.removeEventListener(INFO_EVENT, refreshCheckers);
    if (!submitted && saveTimer) { clearTimeout(saveTimer); saving = saving.then(saveDraft); }
  };
}
