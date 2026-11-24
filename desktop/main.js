// DubEval desktop: starts the Python server (`python -m dubeval web`), reads the launch link it prints, and shows the
// web interface in a window. No terminal; closing the window stops the server.
//
// Proof of concept: Python comes from the repository's .venv (or DUBEVAL_PYTHON). A packaged build will ship its
// own Python next to the app (resources/python), found the same way.
const { app, BrowserWindow, dialog, ipcMain, shell, Menu, Notification } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const updater = require("./updater");

const LAUNCH_LINE = /DubEval: (http:\/\/127\.0\.0\.1:(\d+)\/\?token_given=[\w-]+)/;
const START_TIMEOUT_MS = 120_000;            // the first start imports torch and friends; slow disks take a while
const LANGUAGES = ["en", "ko", "pt", "es"];
const REPO = path.resolve(__dirname, "..");
const DEV_ICON = path.join(__dirname, "build", process.platform === "win32" ? "icon.ico" : "icon.png");
// The start and failure page. Packaged, it sits outside the app's archive (asarUnpack in package.json): with the
// grantFileProtocolExtraPrivileges fuse off, a window can't open a file:// page inside the archive, only blank.
const STATUS_PAGE = path.join(__dirname.replace(/app\.asar$/, "app.asar.unpacked"), "status.html");

let server = null;          // the Python child process
let origin = null;          // http://127.0.0.1:<port>, the only place the window may go
let win = null;
let quitting = false;
const recentOutput = [];    // the server's last lines, shown if it fails to start

// The Python that runs DubEval: an explicit DUBEVAL_PYTHON, a bundled one, else the repository's virtual env.
function findPython() {
  const exe = process.platform === "win32" ? ["Scripts", "python.exe"] : ["bin", "python"];
  const candidates = [
    process.env.DUBEVAL_PYTHON,
    process.resourcesPath && path.join(process.resourcesPath, "python", ...(process.platform === "win32" ? ["python.exe"] : ["bin", "python3"])),
    path.join(REPO, ".venv", ...exe),
  ].filter(Boolean);
  return candidates.find(p => fs.existsSync(p)) || null;
}

// The folder holding a shipped Python (Windows: resources/python/python.exe, macOS: Resources/python/bin/python3
// → resources), or null for a development .venv.
function bundleOf(python) {
  let home = path.dirname(python);
  if (path.basename(home) === "bin") home = path.dirname(home);
  const root = path.basename(home) === "python" ? path.dirname(home) : null;
  return root && fs.existsSync(path.join(root, "build.json")) ? root : null;
}

const MAC = process.platform === "darwin";

const SHOW_WITHIN_MS = 3000;  // the window appears by then even if its first page never draws (a crashed page, say)
const languageFile = () => path.join(app.getPath("userData"), "language.txt");

// The language of the starting page, which opens before the web page and can't read its settings: the one the page
// last told us, else the computer's. A different one here changed the words on screen in the middle of starting.
function language() {
  try {
    const saved = fs.readFileSync(languageFile(), "utf8").trim();
    if (LANGUAGES.includes(saved)) return saved;
  } catch { /* not told yet */ }
  const code = (app.getLocale() || "en").split("-")[0];
  return LANGUAGES.includes(code) ? code : "en";
}

function showStatus(state, detail = "") {
  if (!win) return;
  win.loadFile(STATUS_PAGE, { query: { state, lang: language(), detail: detail.slice(-2000) } });
}

function logFile() {
  const dir = path.join(app.getPath("userData"), "logs");
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, "server.log");
}

// Starts the server; resolves with the launch link, rejects with the reason it couldn't start.
function startServer() {
  return new Promise((resolve, reject) => {
    const python = findPython();
    if (!python) { reject(new Error("no-python")); return; }
    const log = fs.createWriteStream(logFile(), { flags: "w" });
    // --exit-with-parent: the server waits on this process and exits when the app is gone, even after a crash.
    // Its stdin stays closed: a thread reading a stdin pipe froze scipy's first import on Windows.
    const serve = ["-m", "dubeval", "web", "--no-browser", "--exit-with-parent"];
    const bundle = bundleOf(python);
    let options;
    if (bundle) {
      // The shipped Python: isolated from anything installed on this PC (-I ignores PYTHON* variables and the user's
      // site-packages, so -u and -X utf8 replace them); data, history and the .env with API keys live in the
      // app's data folder, the shipped models next to Python.
      const data = path.join(app.getPath("userData"), "data");
      fs.mkdirSync(data, { recursive: true });
      options = { cwd: data, env: { ...process.env, DUBEVAL_DATA: data, DUBEVAL_BUNDLED_MODELS: path.join(bundle, "models") } };
      serve.unshift("-I", "-u", "-X", "utf8");
      if (MAC) {
        // Nothing may change inside the signed app: no compiled Python files (-B; the build ships them, see
        // tools/build_desktop.py) and the audio code's compiled cache goes to the app's data folder.
        serve.unshift("-B");
        options.env.NUMBA_CACHE_DIR = path.join(app.getPath("userData"), "cache", "numba");
      }
    } else {
      options = { cwd: REPO, env: { ...process.env, PYTHONUNBUFFERED: "1", PYTHONUTF8: "1" } };
    }
    options.env.DUBEVAL_NOTIFY = "1";             // the server says when an evaluation ends (see notifyFinished)
    server = spawn(python, serve, { ...options, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
    const timer = setTimeout(() => reject(new Error("timeout")), START_TIMEOUT_MS);
    let found = false;
    const read = chunk => {
      const text = chunk.toString("utf8");
      // The launch link carries this launch's token: keep it out of the log file.
      log.write(text.replace(/token_given=[\w-]+/g, "token_given=<hidden>"));
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        if (line.startsWith(NOTIFY_LINE)) { notifyFinished(line.slice(NOTIFY_LINE.length)); continue; }
        if (line.startsWith(PROGRESS_LINE)) { showProgress(line.slice(PROGRESS_LINE.length)); continue; }
        recentOutput.push(line.replace(/token_given=[\w-]+/g, "token_given=<hidden>"));
        if (recentOutput.length > 40) recentOutput.shift();
        const m = !found && line.match(LAUNCH_LINE);
        if (m) {
          found = true;
          clearTimeout(timer);
          resolve(m[1]);
        }
      }
    };
    server.stdout.on("data", read);
    server.stderr.on("data", read);
    server.on("error", e => { clearTimeout(timer); reject(e); });
    server.on("exit", code => {
      clearTimeout(timer);
      evaluationsLeft = 0;                          // nothing runs any more: quitting has nothing to stop
      log.end();
      server = null;
      if (!found) reject(new Error(`exit-${code}`));
      else if (!quitting) showStatus("stopped", recentOutput.join("\n"));
    });
  });
}

// An evaluation ended by itself (dubeval/webapp.py _notify_app): a system notification, unless the window is in front
// and the person can see it already. A click brings the window forward on that evaluation's screen.
const NOTIFY_LINE = "DubEval-notify: ";
const OPENABLE = /^#\/(report|compare|job)\/[0-9a-f]{12}$/;
// Shown notifications are kept until clicked or closed: one nobody holds can be collected, and a click on it later
// (from Notification Center, minutes on) then only brings the app forward instead of opening the evaluation.
const shownNotes = new Set();
function notifyFinished(text) {
  let note;
  try { note = JSON.parse(text); } catch { return; }
  if (!note || typeof note.title !== "string" || !Notification.isSupported()) return;
  if (win && !win.isDestroyed() && win.isFocused() && win.isVisible() && !win.isMinimized()) return;
  // No icon given: Windows and macOS show the app's own (build/ isn't packaged).
  const shown = new Notification({ title: note.title, body: typeof note.body === "string" ? note.body : "" });
  shownNotes.add(shown);
  const forget = () => shownNotes.delete(shown);
  shown.on("click", () => {
    forget();
    noteLog(`notification clicked: ${note.open}`);
    if (!win || win.isDestroyed()) return;
    if (win.isMinimized()) win.restore();
    win.show();
    win.focus();
    if (typeof note.open === "string" && OPENABLE.test(note.open)) win.webContents.send("app:open", note.open);
  });
  shown.on("close", forget);
  shown.on("failed", forget);
  shown.show();
  noteLog(`notification shown: ${note.open}`);
}

// The running evaluation's progress on the app's icon (dubeval/webapp.py _progress_line): a bar on the Windows taskbar
// button or the Dock icon, so a long run can be followed from another app. A failed run leaves the Windows bar red until
// the window is looked at; the Dock shows how many evaluations are left when some wait in line.
const PROGRESS_LINE = "DubEval-progress: ";
let progressFailed = false;
let evaluationsLeft = 0;          // running + waiting, from the last progress line: quitting stops them (confirmQuit)
function showProgress(text) {
  let note;
  try { note = JSON.parse(text); } catch { return; }
  if (!note || !win || win.isDestroyed()) return;
  progressFailed = false;
  if (note.failed && process.platform === "win32") {
    win.setProgressBar(1, { mode: "error" });
    progressFailed = true;
  } else if (typeof note.progress === "number") {
    win.setProgressBar(Math.min(1, Math.max(0.01, note.progress)));     // 0 would show no bar at all on Windows
  } else {
    win.setProgressBar(-1);
  }
  evaluationsLeft = typeof note.progress === "number" ? 1 + (note.waiting || 0) : 0;
  const left = evaluationsLeft > 1 ? evaluationsLeft : 0;
  if (process.platform === "darwin" && app.dock) app.dock.setBadge(left ? String(left) : "");
}

// Quitting while evaluations run or wait in line stops them all (they come back as stopped, with Continue): asked first,
// once. An update's restart doesn't ask here: its window already said so (w.upd.running_stops).
const QUIT_TEXT = {
  en: { one: "An evaluation is running.", many: "{n} evaluations are running or waiting in line.",
    detail: "If you quit now, they stop. You can continue each one the next time you open DubEval.",
    keep: "Keep DubEval open", quit: "Quit anyway" },
  ko: { one: "평가가 진행 중입니다.", many: "평가 {n}개가 진행 중이거나 대기 중입니다.",
    detail: "지금 종료하면 모두 중지됩니다. 다음에 DubEval을 열 때 하나씩 이어서 할 수 있습니다.",
    keep: "계속 열어 두기", quit: "그래도 종료" },
  pt: { one: "Uma avaliação está em andamento.", many: "{n} avaliações estão em andamento ou na fila.",
    detail: "Se você sair agora, elas param. Você pode continuar cada uma da próxima vez que abrir o DubEval.",
    keep: "Manter o DubEval aberto", quit: "Sair mesmo assim" },
  es: { one: "Hay una evaluación en curso.", many: "Hay {n} evaluaciones en curso o en cola.",
    detail: "Si sales ahora, se detienen. Puedes continuar cada una la próxima vez que abras DubEval.",
    keep: "Mantener DubEval abierto", quit: "Salir de todos modos" },
};
let quitConfirmed = false, installingUpdate = false;
function confirmQuit() {
  if (quitConfirmed || installingUpdate || evaluationsLeft === 0) return true;
  const text = QUIT_TEXT[language()] || QUIT_TEXT.en;
  const choice = dialog.showMessageBoxSync(win && !win.isDestroyed() ? win : undefined, {
    type: "warning", title: "DubEval", buttons: [text.keep, text.quit], defaultId: 0, cancelId: 0, noLink: true,
    message: evaluationsLeft === 1 ? text.one : text.many.replace("{n}", String(evaluationsLeft)), detail: text.detail });
  quitConfirmed = choice === 1;
  return quitConfirmed;
}

// One line in update.log next to server.log (the app's own events; the server's go to server.log).
function noteLog(line) {
  try { fs.appendFileSync(path.join(path.dirname(logFile()), "update.log"), `${new Date().toISOString()} ${line}
`); }
  catch { /* no log */ }
}

// Stops the server and everything it started (on Windows, the whole process tree). Synchronous: the app is about to
// exit, and an asynchronous stop would be cut off with it, leaving Python running.
function stopServer() {
  if (!server) return;
  const pid = server.pid;
  server = null;
  if (process.platform === "win32") spawnSync("taskkill", ["/pid", String(pid), "/T", "/F"], { windowsHide: true });
  else { try { process.kill(pid, "SIGTERM"); } catch { /* already gone */ } }
}

function createWindow() {
  win = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: "DubEval",
    show: false,                                       // until its first page is drawn: no empty window first
    autoHideMenuBar: true,
    backgroundColor: "#0e131b",
    // No white Windows title bar (as in PersoDub): the page's dark top strip is the title bar and the window buttons
    // are drawn over its right end in the same colours. 36 px = the strip's height (.topbar in the page's CSS).
    // On macOS the three window buttons sit at the strip's left end, centred in its 36 px.
    titleBarStyle: "hidden",
    ...(MAC ? { trafficLightPosition: { x: 14, y: 11 } }
      : { titleBarOverlay: { color: "#0e131b", symbolColor: "#e6e8eb", height: 36 } }),
    ...(fs.existsSync(DEV_ICON) ? { icon: DEV_ICON } : {}),   // packaged: the icon stamped into DubEval.exe
    // preload.js gives the page window.dubevalShell (updates only); it stays sandboxed, with no Node.
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true,
      preload: path.join(__dirname, "preload.js") },
  });
  // Only DubEval's own pages open in the window (the server's, and this app's status page, no other local file);
  // other links go to the person's browser.
  const statusPage = pathToFileURL(STATUS_PAGE).href;
  win.webContents.on("will-navigate", (event, url) => {
    if (url.split(/[?#]/)[0] === statusPage || (origin && new URL(url).origin === origin)) return;
    event.preventDefault();
    openOutside(url);
  });
  if (process.platform === "win32" && !app.isPackaged && fs.existsSync(DEV_ICON)) {
    // Run from the repository, the taskbar button shows electron.exe's icon whatever the window's own is: the window's
    // relaunch icon (its own taskbar id) makes it DubEval's. Packaged, DubEval.exe carries the icon itself.
    win.setAppDetails({ appId: "org.dubeval.desktop.dev", appIconPath: DEV_ICON, appIconIndex: 0,
      relaunchDisplayName: "DubEval" });
  }
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (origin && new URL(url).origin === origin) {
      return { action: "allow", overrideBrowserWindowOptions: { autoHideMenuBar: true,
        webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } } };
    }
    openOutside(url);
    return { action: "deny" };
  });
  const show = () => { if (win && !win.isVisible()) win.show(); };
  win.once("ready-to-show", show);
  setTimeout(show, SHOW_WITHIN_MS);
  win.on("close", event => { if (!confirmQuit()) event.preventDefault(); });
  win.on("closed", () => { win = null; });
  win.on("focus", () => {                          // the red bar of a failed run has been seen
    if (progressFailed && win && !win.isDestroyed()) { win.setProgressBar(-1); progressFailed = false; }
  });
  showStatus("starting");
}

function openOutside(url) {
  if (/^https?:\/\//i.test(url)) shell.openExternal(url);
}

async function launch() {
  createWindow();
  try {
    const link = await startServer();
    origin = new URL(link).origin;
    if (win) await win.loadURL(link);
  } catch (e) {
    stopServer();
    const reason = e.message === "no-python" ? "no-python" : e.message === "timeout" ? "timeout" : "failed";
    showStatus(reason, recentOutput.join("\n"));
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) { if (win.isMinimized()) win.restore(); win.show(); win.focus(); }
  });
  // Windows shows an app's notifications under the id its Start menu shortcut carries (electron-builder: build.appId).
  if (process.platform === "win32") app.setAppUserModelId(app.isPackaged ? "org.dubeval.desktop" : process.execPath);
  app.whenReady().then(() => {
    // No menu bar on Windows. macOS always shows one, and its Edit menu is what makes Cmd+C, Cmd+V and Cmd+A work in
    // the page's text boxes, so it gets the standard three: the app's own (About, Hide, Quit), Edit and Window.
    if (MAC) Menu.setApplicationMenu(Menu.buildFromTemplate([{ role: "appMenu" }, { role: "editMenu" }, { role: "windowMenu" }]));
    else if (app.isPackaged) Menu.setApplicationMenu(null);
    ipcMain.on("language", (event, code) => {
      const from = event.senderFrame && event.senderFrame.url;
      if (!origin || !from || new URL(from).origin !== origin || !LANGUAGES.includes(code)) return;
      try { fs.writeFileSync(languageFile(), code); } catch { /* the next start uses the computer's */ }
    });
    updater.init({
      getWindow: () => win,
      isOwnPage: url => !!(origin && url && new URL(url).origin === origin),
      log: line => { try { fs.appendFileSync(path.join(path.dirname(logFile()), "update.log"), `${new Date().toISOString()} ${line}
`); } catch { /* no log */ } },
      onInstall: () => { installingUpdate = true; },
    });
    launch();
  });
  app.on("before-quit", event => {
    if (!confirmQuit()) { event.preventDefault(); return; }    // Cmd+Q on a Mac comes here before any window closes
    quitting = true;
    stopServer();
  });
  app.on("window-all-closed", () => app.quit());
}
