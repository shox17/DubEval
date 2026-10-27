// Updates, as PersoDub does them: electron-updater looks for a newer release of the repository in package.json's
// build.publish (GitHub Releases: the installer and its latest.yml), downloads it in the background and installs it
// on "Restart to update" or, failing that, the next time the app quits. The page follows along through preload.js:
// {phase: idle | checking | none | downloading | ready | error, version, pct, releaseDate, releaseNotes}: the date and
// the notes are the GitHub release's (its body; the page shows it as plain lines).
//
// Only a packaged app updates. DUBEVAL_UPDATE_URL points it at another feed (a folder served over HTTP with
// latest.yml and the installer), to try a release before publishing it.
const { app, ipcMain } = require("electron");

const CHECK_EVERY_MS = 4 * 60 * 60 * 1000;
const FIRST_CHECK_MS = 10_000;

let state = { phase: "idle" };
let updater = null;

function init({ getWindow, isOwnPage, log }) {
  const send = () => { const w = getWindow(); if (w && !w.isDestroyed()) w.webContents.send("update:state", state); };
  const set = next => { state = next; send(); };
  // Only DubEval's own page may ask (the window shows nothing else, but the check costs nothing).
  const own = handler => (event, ...args) => (isOwnPage(event.senderFrame && event.senderFrame.url) ? handler(...args)
    : undefined);
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
  updater.autoInstallOnAppQuit = true;
  updater.disableWebInstaller = true;                  // DubEval ships the full installer only
  updater.logger = { info: () => {}, warn: m => log(`update: ${m}`), error: m => log(`update error: ${m}`), debug: () => {} };
  if (process.env.DUBEVAL_UPDATE_URL) updater.setFeedURL({ provider: "generic", url: process.env.DUBEVAL_UPDATE_URL });
  updater.on("checking-for-update", () => { if (state.phase !== "downloading" && state.phase !== "ready") set({ phase: "checking" }); });
  updater.on("update-not-available", () => set({ phase: "none" }));
  const about = info => ({ version: info.version, releaseDate: info.releaseDate || null,
    releaseNotes: info.releaseNotes || null });
  updater.on("update-available", info => set({ phase: "downloading", ...about(info), pct: 0 }));
  updater.on("download-progress", p => set({ ...state, phase: "downloading", pct: p.percent }));
  updater.on("update-downloaded", info => set({ ...state, phase: "ready", ...about(info) }));
  updater.on("error", e => {
    log(`update error: ${e && e.message}`);
    if (state.phase !== "ready") set({ phase: "error" });
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
