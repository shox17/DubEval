// What the page may ask of the desktop app: updates (see updater.js), and to start in its language next time. The page stays sandboxed, with no
// Node; it sees only window.dubevalShell. In a plain browser the object is missing and the page hides updates.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dubevalShell", {
  rememberLanguage: code => ipcRenderer.send("language", code),
  getUpdate: () => ipcRenderer.invoke("update:get"),
  checkForUpdates: () => ipcRenderer.invoke("update:check"),
  restartToUpdate: () => ipcRenderer.invoke("update:restart"),
  justUpdated: () => ipcRenderer.invoke("update:just-updated"),
  onUpdate: callback => { ipcRenderer.on("update:state", (_event, state) => callback(state)); },
});
