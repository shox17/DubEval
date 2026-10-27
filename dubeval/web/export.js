// Export, as in PersoDub: a dialog listing what a finished evaluation can be saved as. One file downloads as it is;
// several come as one ZIP. The files are written in the page's language (GET /api/jobs/{id}/export).
import { h, openModal, state, t } from "./app.js";

const KINDS = [
  { id: "html", checked: true }, { id: "xlsx", checked: true }, { id: "text" }, { id: "json" },
];

export function exportButton(jobId) {
  return h("button", { type: "button", class: "primary", onclick: () => exportDialog(jobId) }, t("w.exp.button"));
}

function exportDialog(jobId) {
  const boxes = KINDS.map(k => h("input", { type: "checkbox", value: k.id, checked: !!k.checked }));
  const error = h("p", { class: "error", role: "alert" });
  const list = h("div", { class: "export-list" }, KINDS.map((k, i) =>
    h("label", { class: "export-row" }, boxes[i],
      h("span", {}, h("b", {}, t(`w.exp.${k.id}`)), h("span", { class: "muted small" }, t(`w.exp.${k.id}_hint`))))));
  openModal(t("w.exp.title"), [list, h("p", { class: "muted small export-note" }, t("w.exp.zip_note")), error], [
    { label: t("w.cancel") },
    { label: t("w.exp.button"), primary: true, onclick: close => {
      const kinds = boxes.filter(b => b.checked).map(b => b.value);
      if (!kinds.length) { error.textContent = t("w.exp.none"); return; }
      const a = h("a", { href: `/api/jobs/${encodeURIComponent(jobId)}/export?kinds=${kinds.join(",")}&lang=${state.lang}`,
        download: "" });
      document.body.append(a);
      a.click();
      a.remove();
      close();
    } },
  ], { width: 420 });
}
