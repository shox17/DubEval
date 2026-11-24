// What the page may ask of the desktop app: updates (see updater.js), and to start in its language next time. The page stays sandboxed, with no
// Node; it sees only window.dubevalShell. In a plain browser the object is missing and the page hides updates.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dubevalShell", {
  // Every build updates itself, Windows and macOS (updater.js). A shell that can't would say false here, and the page
  // then points to the releases page instead (w.upd.by_hand).
  selfUpdates: true,
  rememberLanguage: code => ipcRenderer.send("language", code),
  getUpdate: () => ipcRenderer.invoke("update:get"),
  checkForUpdates: () => ipcRenderer.invoke("update:check"),
  restartToUpdate: () => ipcRenderer.invoke("update:restart"),
  justUpdated: () => ipcRenderer.invoke("update:just-updated"),
  onUpdate: callback => { ipcRenderer.on("update:state", (_event, state) => callback(state)); },
  // A click on the "finished" notification (main.js notifyFinished): the screen to open, such as "#/report/<id>".
  onOpen: callback => { ipcRenderer.on("app:open", (_event, hash) => callback(hash)); },
});
