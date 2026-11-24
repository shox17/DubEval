// Export, as in PersoDub: a dialog listing what a finished evaluation can be saved as. One file downloads as it is;
// several come as one ZIP. The files are written in the page's language (GET /api/jobs/{id}/export).
// Problem clips take a few seconds each, so with them the dialog stays open and says how many until the ZIP is ready.
import { h, openModal, state, t } from "./app.js";

const KINDS = [
  { id: "html", checked: true }, { id: "xlsx", checked: true }, { id: "clips" }, { id: "text" }, { id: "json" },
];

// moments: each dub's number of moments on the timeline, so the wait for clips can say how many it makes.
export function exportButton(jobId, moments = []) {
  return h("button", { type: "button", class: "primary", onclick: () => exportDialog(jobId, moments) }, t("w.exp.button"));
}

// How many clips Export makes: one per moment, at most clips_max per dub (the worst kept).
function clipCount(moments) {
  const most = state.info?.clips_max || Infinity;
  return moments.reduce((sum, n) => sum + Math.min(n || 0, most), 0);
}

// The file name the server gave (Content-Disposition), UTF-8 form first.
function fileName(res) {
  const header = res.headers.get("Content-Disposition") || "";
  const utf = header.match(/filename\*=utf-8''([^;]+)/i);
  if (utf) { try { return decodeURIComponent(utf[1]); } catch { /* the plain one */ } }
  const plain = header.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : "DubEval.zip";
}

function save(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function exportDialog(jobId, moments) {
  const boxes = KINDS.map(k => h("input", { type: "checkbox", value: k.id, checked: !!k.checked }));
  const error = h("p", { class: "error", role: "alert" });
  const count = clipCount(moments);
  const making = h("p", { class: "muted small export-making", hidden: true }, h("span", { class: "spinner" }),
    count ? t(count === 1 ? "w.exp.making_one" : "w.exp.making_many", { n: count }) : t("w.exp.making"));
  const list = h("div", { class: "export-list" }, KINDS.map((k, i) =>
    h("label", { class: "export-row" }, boxes[i],
      h("span", {}, h("b", {}, t(`w.exp.${k.id}`)), h("span", { class: "muted small" }, t(`w.exp.${k.id}_hint`))))));
  let working = null;                       // the clips' request, stopped if the dialog is closed
  openModal(t("w.exp.title"), [list, h("p", { class: "muted small export-note" }, t("w.exp.zip_note")), making, error], [
    { label: t("w.cancel"), onclick: close => { working?.abort(); close(); } },
    { label: t("w.exp.button"), primary: true, onclick: async (close, button) => {
      const kinds = boxes.filter(b => b.checked).map(b => b.value);
      if (!kinds.length) { error.textContent = t("w.exp.none"); return; }
      const url = `/api/jobs/${encodeURIComponent(jobId)}/export?kinds=${kinds.join(",")}&lang=${state.lang}`;
      if (!kinds.includes("clips")) {
        const a = h("a", { href: url, download: "" });
        document.body.append(a);
        a.click();
        a.remove();
        close();
        return;
      }
      error.textContent = "";
      making.hidden = false;
      boxes.forEach(b => { b.disabled = true; });
      if (button) button.disabled = true;
      working = new AbortController();
      try {
        const res = await fetch(url, { credentials: "same-origin", headers: { "Accept-Language": state.lang },
          signal: working.signal });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `${res.status} ${res.statusText}`);
        }
        save(await res.blob(), fileName(res));
        close();
      } catch (e) {
        if (e.name === "AbortError") return;
        error.textContent = e.message;
        making.hidden = true;
        boxes.forEach(b => { b.disabled = false; });
        if (button) button.disabled = false;
      }
    } },
  ], { width: 460 });
}
