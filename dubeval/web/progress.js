// Progress screen: the stage checklist and a bar, polled once a second; opens the review when the job is done.
import { api, confirmAlert, go, h, state, t } from "./app.js";

const POLL_MS = 1000;

function elapsed(sec) {
  const m = Math.floor(sec / 60), s = Math.round(sec % 60);
  return m ? `${m}:${String(s).padStart(2, "0")}` : `${s} s`;
}

// A stage's mark, as PersoDub's: a green circled tick when done, a red circled cross when it failed, a stop square
// where you stopped it, a spinning ring for the stage running, an empty ring for the ones to come.
const MARKS = { done: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "m16 9-5.5 5.5L8 12"],
  failed: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "m15 9-6 6", "m9 9 6 6"],
  stopped: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "M9 9h6v6H9z"] };

function stageMark(stageState) {
  const mark = h("span", { class: `step-mark ${stageState}`, "aria-hidden": "true" });
  if (MARKS[stageState]) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    for (const d of MARKS[stageState]) {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", d);
      svg.append(path);
    }
    mark.append(svg);
  }
  return mark;
}

// The server marks the stage a job ended in as "failed"; a job you stopped shows it as stopped instead.
function stageRows(stages, cancelled = false) {
  return stages.map(s => {
    const mark = cancelled && s.state === "failed" ? "stopped" : s.state;
    return h("li", { class: mark }, stageMark(mark), h("span", {}, t(`stage.${s.id}`)));
  });
}

export function renderProgress(root, jobId) {
  const list = h("ol", { class: "stages" });
  const bar = h("progress", { max: "1", value: "0" });
  const message = h("p", { class: "message" });
  const time = h("span", { class: "muted" });
  let draftId = null, stopping = false;
  const over = new AbortController();         // closes the Stop question once the evaluation ends or the page is left
  // Stop asks first, as PersoDub does: what's done so far is lost (the draft, if any, keeps what was filled in).
  const stop = h("button", { type: "button", onclick: async () => {
    const stopped = await confirmAlert({ title: t("w.progress.stop_title"),
      text: t(draftId ? "w.progress.stop_text_draft" : "w.progress.stop_text"),
      keep: t("w.progress.keep"), confirm: t("w.progress.stop"),
      onConfirm: () => api(`/api/jobs/${jobId}/cancel`, { method: "POST" }), signal: over.signal });
    if (!stopped) return;
    stopping = true;
    stop.disabled = true;
    stop.textContent = t("w.progress.stopping");
    message.textContent = t("w.progress.stopping");
  } }, t("w.progress.stop"));
  const box = h("section", { class: "progress card" }, h("h1", {}, t("w.progress.title")), list, bar,
    h("div", { class: "row" }, message, h("span", { class: "grow" }), time), h("div", { class: "actions" }, stop));
  root.append(box);
  let timer = null, alive = true;

  async function poll() {
    let job;
    try {
      job = await api(`/api/jobs/${jobId}?lang=${state.lang}`);
    } catch (e) {
      box.replaceChildren(h("h1", {}, t("w.progress.failed")), h("p", { class: "error" }, e.message),
        h("div", { class: "actions" }, h("a", { class: "button", href: "#/" }, t("w.progress.back"))));
      return;
    }
    if (!alive) return;
    if (job.status !== "running") over.abort();
    if (job.status === "done") {
      // Replaced, not added: Back from the result goes to where the evaluation was started, not to this screen.
      go(`#/${job.kind === "comparison" ? "compare" : "report"}/${jobId}`, { replace: true });
      return;
    }
    draftId = job.draft_id;
    list.replaceChildren(...stageRows(job.stages, job.status === "cancelled"));
    bar.value = job.progress;
    message.textContent = stopping ? t("w.progress.stopping") : job.message;
    time.textContent = elapsed(job.elapsed_sec);
    if (job.status === "running") { timer = setTimeout(poll, POLL_MS); return; }
    const cancelled = job.status === "cancelled";
    // As PersoDub's stopped screen: why it stopped, then Continue (the same evaluation again, picking up what was
    // already measured), a way to change it first (its draft), and the way back.
    const error = h("p", { class: "error", role: "alert" });
    const resume = job.can_continue ? h("button", { type: "button", class: "primary", onclick: async () => {
      resume.disabled = true;
      error.textContent = "";
      try {
        const next = await api(`/api/jobs/${jobId}/continue`, { method: "POST" });
        go(`#/job/${next.id}`);
      } catch (e) { error.textContent = e.message; resume.disabled = false; }
    } }, t("w.progress.continue")) : null;
    box.replaceChildren(h("h1", {}, cancelled ? t("w.progress.stopped") : t("w.progress.failed")), list,
      cancelled ? h("p", { class: "muted" }, t(job.can_continue ? "w.progress.stopped_continue" : "w.progress.stopped_text"))
        : h("p", { class: "error" }, job.error || ""), error,
      h("div", { class: "actions" }, h("a", { class: "button", href: "#/" }, t("w.nav.evaluations")),
        h("a", { class: `button${resume ? "" : " primary"}`, href: job.draft_id ? `#/draft/${job.draft_id}` : "#/new" },
          t(job.draft_id ? "w.progress.edit" : "w.progress.back")),
        resume));
  }
  poll();
  return () => { alive = false; clearTimeout(timer); over.abort(); };
}
