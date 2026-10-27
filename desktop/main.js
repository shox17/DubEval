// DubEval desktop: starts the Python server (`python -m dubeval web`) on a free port, reads the launch link it
// prints, and shows the web interface in a window. No terminal; closing the window stops the server.
//
// Proof of concept: Python comes from the repository's .venv (or DUBEVAL_PYTHON). A packaged build will ship its
// own Python next to the app (resources/python), found the same way.
const { app, BrowserWindow, shell, Menu } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const updater = require("./updater");

const LAUNCH_LINE = /DubEval: (http:\/\/127\.0\.0\.1:(\d+)\/\?token_given=[\w-]+)/;
const START_TIMEOUT_MS = 120_000;            // the first start imports torch and friends; slow disks take a while
const LANGUAGES = ["en", "ko", "pt", "es"];
const REPO = path.resolve(__dirname, "..");
const DEV_ICON = path.join(__dirname, "build", "icon.png");

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

// The folder holding a shipped Python (resources/python/python.exe → resources), or null for a development .venv.
function bundleOf(python) {
  const home = path.dirname(python);
  const root = path.basename(home) === "python" ? path.dirname(home) : null;
  return root && fs.existsSync(path.join(root, "build.json")) ? root : null;
}

function language() {
  const code = (app.getLocale() || "en").split("-")[0];
  return LANGUAGES.includes(code) ? code : "en";
}

function showStatus(state, detail = "") {
  if (!win) return;
  win.loadFile(path.join(__dirname, "status.html"), { query: { state, lang: language(), detail: detail.slice(-2000) } });
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
    const serve = ["-m", "dubeval", "web", "--port", "0", "--no-browser", "--exit-with-parent"];
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
    } else {
      options = { cwd: REPO, env: { ...process.env, PYTHONUNBUFFERED: "1", PYTHONUTF8: "1" } };
    }
    server = spawn(python, serve, { ...options, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
    const timer = setTimeout(() => reject(new Error("timeout")), START_TIMEOUT_MS);
    let found = false;
    const read = chunk => {
      const text = chunk.toString("utf8");
      // The launch link carries this launch's token: keep it out of the log file.
      log.write(text.replace(/token_given=[\w-]+/g, "token_given=<hidden>"));
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
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
      log.end();
      server = null;
      if (!found) reject(new Error(`exit-${code}`));
      else if (!quitting) showStatus("stopped", recentOutput.join("\n"));
    });
  });
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
    autoHideMenuBar: true,
    backgroundColor: "#0e131b",
    // No white Windows title bar (as in PersoDub): the page's dark top strip is the title bar and the window buttons
    // are drawn over its right end in the same colours. 36 px = the strip's height (.topbar in the page's CSS).
    titleBarStyle: "hidden",
    titleBarOverlay: { color: "#0e131b", symbolColor: "#e6e8eb", height: 36 },
    ...(fs.existsSync(DEV_ICON) ? { icon: DEV_ICON } : {}),   // packaged: the icon stamped into DubEval.exe
    // preload.js gives the page window.dubevalShell (updates only); it stays sandboxed, with no Node.
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true,
      preload: path.join(__dirname, "preload.js") },
  });
  // Only DubEval's own pages open in the window (the server's, and this app's status page, no other local file);
  // other links go to the person's browser.
  const statusPage = pathToFileURL(path.join(__dirname, "status.html")).href;
  win.webContents.on("will-navigate", (event, url) => {
    if (url.split(/[?#]/)[0] === statusPage || (origin && new URL(url).origin === origin)) return;
    event.preventDefault();
    openOutside(url);
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (origin && new URL(url).origin === origin) {
      return { action: "allow", overrideBrowserWindowOptions: { autoHideMenuBar: true,
        webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } } };
    }
    openOutside(url);
    return { action: "deny" };
  });
  win.on("closed", () => { win = null; });
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
    if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
  });
  app.whenReady().then(() => {
    if (app.isPackaged) Menu.setApplicationMenu(null);
    updater.init({
      getWindow: () => win,
      isOwnPage: url => !!(origin && url && new URL(url).origin === origin),
      log: line => { try { fs.appendFileSync(path.join(path.dirname(logFile()), "update.log"), `${new Date().toISOString()} ${line}
`); } catch { /* no log */ } },
    });
    launch();
  });
  app.on("before-quit", () => { quitting = true; stopServer(); });
  app.on("window-all-closed", () => app.quit());
}
