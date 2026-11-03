// Updates, as PersoDub does them: electron-updater looks for a newer release of the repository in package.json's
// build.publish (GitHub Releases: the installer and its latest.yml), downloads it in the background and installs it
// only on "Restart to update": simply closing the app leaves it as it is. The page follows along through preload.js:
// {phase: idle | checking | none | downloading | ready | download-failed | error, version, pct, releaseDate,
// releaseNotes, whatsNew}: the date and the notes are the GitHub release's (its body; the page shows it as plain lines),
// whatsNew that version's own lines in every language (dubeval/release_notes.json at its tag).
//
// Only a packaged app updates. DUBEVAL_UPDATE_URL points it at another feed (a folder served over HTTP with
// latest.yml, the installer and release_notes.json), to try a release before publishing it.
const { app, ipcMain, net } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const CHECK_EVERY_MS = 4 * 60 * 60 * 1000;
const FIRST_CHECK_MS = 10_000;
const NOTES_TIMEOUT_MS = 5000;
const REPOSITORY_FILES = "https://raw.githubusercontent.com/shox17/DubEval";

// An error as one log line: electron-updater's HTTP errors carry the whole response's headers in their message.
const errorLine = e => String((e && e.message) || e).split(/\r?\n/)[0].replace(/\?\S*/g, "").slice(0, 300);

// The new version's own lines, {en: [...], ko: [...], ...}, or null when they can't be read in time or it has none: the
// window then shows the release's description, which is in English only.
async function readWhatsNew(version, log) {
  const feed = process.env.DUBEVAL_UPDATE_URL;
  const url = feed ? `${feed.replace(/\/$/, "")}/release_notes.json`
    : `${REPOSITORY_FILES}/v${version}/dubeval/release_notes.json`;
  try {
    const answer = await net.fetch(url, { signal: AbortSignal.timeout(NOTES_TIMEOUT_MS) });
    if (!answer.ok) throw new Error(`HTTP ${answer.status}`);
    const lines = {};
    for (const [lang, list] of Object.entries((await answer.json())[version] || {})) {
      if (Array.isArray(list)) lines[lang] = list.filter(l => typeof l === "string" && l.trim());
    }
    return Object.values(lines).some(list => list.length) ? lines : null;
  } catch (e) {
    log(`update notes: ${errorLine(e)}`);
    return null;
  }
}

let state = { phase: "idle" };
let updater = null;

// Whether this is the first run of a new version, for the page's "Updated to X". Kept in a file, not in the page's own
// storage: that belongs to the page's address, which moves when the usual port is busy and was new at every launch up
// to 0.1.3.
function justUpdated() {
  const folder = app.getPath("userData");
  const file = path.join(folder, "last-version.txt");
  let last = null;
  try { last = fs.readFileSync(file, "utf8").trim(); } catch { /* not there yet */ }
  if (last === app.getVersion()) return false;
  try { fs.writeFileSync(file, app.getVersion()); } catch { /* not kept: the next launch says it again */ }
  // No file but earlier logs: a version from before this file ran here.
  return last !== null || fs.existsSync(path.join(folder, "logs", "server.log"));
}

function init({ getWindow, isOwnPage, log }) {
  const send = () => { const w = getWindow(); if (w && !w.isDestroyed()) w.webContents.send("update:state", state); };
  const set = next => { state = next; send(); };
  // Only DubEval's own page may ask (the window shows nothing else, but the check costs nothing).
  const own = handler => (event, ...args) => (isOwnPage(event.senderFrame && event.senderFrame.url) ? handler(...args)
    : undefined);
  let updated = justUpdated();
  ipcMain.handle("update:just-updated", own(() => { const answer = updated; updated = false; return answer; }));
  ipcMain.handle("update:get", own(() => state));
  ipcMain.handle("update:check", own(() => check()));
  ipcMain.handle("update:restart", own(() => {
    // Not silent: the installer's own window shows its progress bar (an update skips its setup pages), then DubEval
    // starts again. Silent left the person with no window at all for minutes.
    if (updater && state.phase === "ready") updater.quitAndInstall(false, true);
  }));
  if (!app.isPackaged) return;

  ({ autoUpdater: updater } = require("electron-updater"));
  updater.autoDownload = true;
  updater.autoInstallOnAppQuit = false;                // the person picks the moment, with "Restart to update"
  updater.allowPrerelease = false;
  updater.disableWebInstaller = true;                  // DubEval ships the full installer only
  updater.logger = { info: () => {}, warn: m => log(`update: ${errorLine(m)}`), error: m => log(`update error: ${errorLine(m)}`), debug: () => {} };
  if (process.env.DUBEVAL_UPDATE_URL) updater.setFeedURL({ provider: "generic", url: process.env.DUBEVAL_UPDATE_URL });
  let found = null;                                    // the update found, from the moment it starts downloading
  updater.on("checking-for-update", () => {
    if (state.phase !== "downloading" && state.phase !== "ready") { found = null; set({ phase: "checking" }); }
  });
  updater.on("update-not-available", () => set({ phase: "none" }));
  const about = info => ({ version: info.version, releaseDate: info.releaseDate || null,
    releaseNotes: info.releaseNotes || null });
  updater.on("update-available", async info => {
    found = about(info);
    // Read first, so the window opens on these lines. The download doesn't wait: if it has finished or broken by now,
    // what that announced stands and only the lines are added.
    const whatsNew = await readWhatsNew(info.version, log);
    set(state.version === info.version ? { ...state, whatsNew } : { phase: "downloading", ...found, pct: 0, whatsNew });
  });
  updater.on("download-progress", p => {
    const pct = Math.round(p.percent);                 // it reports many times a second; the page shows whole percents
    if (state.version && pct !== state.pct) set({ ...state, pct });
  });
  updater.on("update-downloaded", info => set({ ...state, phase: "ready", pct: 100, ...about(info) }));
  updater.on("error", e => {
    log(`update error: ${errorLine(e)}`);
    if (state.phase === "ready") return;
    // A download that broke keeps its version: the window says so, not a button left at its last percent.
    set(found ? { ...state, ...found, phase: "download-failed" } : { phase: "error" });
  });
  setTimeout(check, FIRST_CHECK_MS);
  setInterval(check, CHECK_EVERY_MS);
}

async function check() {
  if (!updater) return state;
  if (state.phase === "downloading" || state.phase === "ready") return state;
  try { await updater.checkForUpdates(); } catch { /* reported through the "error" event */ }
  return state;
}

module.exports = { init };
