// Progress screen: the stage checklist and a bar, polled once a second; opens the review when the job is done.
import { api, confirmAlert, go, h, state, t } from "./app.js";

const POLL_MS = 1000;

function elapsed(sec) {
  const m = Math.floor(sec / 60), s = Math.round(sec % 60);
  return m ? `${m}:${String(s).padStart(2, "0")}` : `${s} s`;
}

// The server's estimate of what's left (from this computer's past evaluations), in whole minutes; none when it has
// no honest one yet.
function left(sec) {
  if (sec == null) return "";
  if (sec < 60) return t("w.progress.left_soon");
  const n = Math.round(sec / 60);
  return n === 1 ? t("w.progress.left_one") : t("w.progress.left_many", { n });
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
  let draftId = null, stopping = false, after = 0;
  const over = new AbortController();         // closes the Stop question once the evaluation ends or the page is left
  // Stop asks first, as PersoDub does: what's done so far is lost (the draft, if any, keeps what was filled in).
  let waiting = false;
  const stop = h("button", { type: "button", onclick: async () => {
    // One waiting in line has measured nothing yet: it leaves the line without a question.
    if (waiting) {
      stop.disabled = true;
      await api(`/api/jobs/${jobId}/cancel`, { method: "POST" }).catch(() => { stop.disabled = false; });
      clearTimeout(timer);
      poll();
      return;
    }
    // with evaluations in line, the next one starts as soon as this one stops: the question says so
    const text = t(draftId ? "w.progress.stop_text_draft" : "w.progress.stop_text");
    const stopped = await confirmAlert({ title: t("w.progress.stop_title"),
      text: after ? `${text} ${t("w.progress.stop_next")}` : text,
      keep: t("w.progress.keep"), confirm: t("w.progress.stop"),
      onConfirm: () => api(`/api/jobs/${jobId}/cancel`, { method: "POST" }), signal: over.signal });
    if (!stopped) return;
    stopping = true;
    stop.disabled = true;
    stop.textContent = t("w.progress.stopping");
    message.textContent = t("w.progress.stopping");
  } }, t("w.progress.stop"));
  const what = h("p", { class: "muted progress-what" });    // which video (or dubs) this is, once the job says
  const title = h("h1", {}, t("w.progress.title"));
  // Another evaluation can be set up meanwhile: it waits in line and starts when this one ends.
  const another = h("a", { class: "button", href: "#/new" }, t("w.progress.another"));
  // While it waits: which evaluation is running, and a way to it (instead of an empty bar that looks stuck).
  const waitingFor = h("p", { class: "waiting-for", hidden: true });
  const line = h("p", { class: "muted small", hidden: true });       // how many wait after the running one
  const progressRow = h("div", { class: "row" }, message, h("span", { class: "grow" }), time);
  const box = h("section", { class: "progress card" }, title, what, waitingFor, list, bar, progressRow, line,
    h("div", { class: "actions" }, another, h("span", { class: "grow" }), stop));
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
    const live = job.status === "running" || job.status === "queued";
    if (!live) over.abort();
    if (job.status === "done") {
      // Replaced, not added: Back from the result goes to where the evaluation was started, not to this screen.
      go(`#/${job.kind === "comparison" ? "compare" : "report"}/${jobId}`, { replace: true });
      return;
    }
    draftId = job.draft_id;
    const names = (job.dub_names || []).filter(Boolean);
    what.textContent = names.length > 1 ? names.map((n, i) => `${"ABCDEFGH"[i]}: ${n}`).join(" · ") : names[0] || "";
    what.hidden = !names.length;
    list.replaceChildren(...stageRows(job.stages, job.status === "cancelled"));
    bar.value = job.progress;
    waiting = job.status === "queued";
    after = job.waiting_after || 0;
    title.textContent = t(waiting ? "w.progress.waiting_title" : "w.progress.title");
    list.hidden = bar.hidden = waiting;
    waitingFor.hidden = !(waiting && job.waiting_for);
    if (!waitingFor.hidden) {
      waitingFor.replaceChildren(t("w.progress.waiting_for", { name: job.waiting_for.name || "…" }), " ",
        h("a", { href: `#/job/${job.waiting_for.id}` }, t("w.progress.open_running")));
    }
    line.hidden = waiting || !after;
    line.textContent = after ? t(after === 1 ? "w.progress.after_one" : "w.progress.after_many", { n: after }) : "";
    stop.textContent = stopping ? t("w.progress.stopping") : t(waiting ? "w.progress.leave_queue" : "w.progress.stop");
    message.textContent = stopping ? t("w.progress.stopping")
      : waiting && job.queue_position ? t(job.queue_position === 1 ? "w.progress.waiting_next" : "w.progress.waiting_n",
        { n: job.queue_position }) : job.message;
    const rest = job.status === "running" && !stopping ? left(job.remaining_sec) : "";
    time.textContent = waiting ? "" : rest ? `${elapsed(job.elapsed_sec)} · ${rest}` : elapsed(job.elapsed_sec);
    if (live) { timer = setTimeout(poll, POLL_MS); return; }
    const cancelled = job.status === "cancelled";
    if (job.removed) {
      // Taken out of the line before it started: nothing was measured, so no "stopped" story and no Continue.
      const error = h("p", { class: "error", role: "alert" });
      const again = h("button", { type: "button", class: "primary", onclick: async () => {
        again.disabled = true;
        try {
          const next = await api(`/api/jobs/${jobId}/continue`, { method: "POST" });
          go(`#/job/${next.id}`);
        } catch (e) { error.textContent = e.message; again.disabled = false; }
      } }, t("w.progress.requeue"));
      box.replaceChildren(h("h1", {}, t("w.progress.removed_title")), what, h("p", { class: "muted" }, job.error || ""),
        error, h("div", { class: "actions" }, h("a", { class: "button", href: "#/" }, t("w.nav.evaluations")),
          job.draft_id ? h("a", { class: "button", href: `#/draft/${job.draft_id}` }, t("w.progress.edit")) : null,
          h("span", { class: "grow" }), again));
      return;
    }
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
