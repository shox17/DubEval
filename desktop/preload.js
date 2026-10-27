// What the page may ask of the desktop app: nothing but updates (see updater.js). The page stays sandboxed, with no
// Node; it sees only window.dubevalShell. In a plain browser the object is missing and the page hides updates.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dubevalShell", {
  getUpdate: () => ipcRenderer.invoke("update:get"),
  checkForUpdates: () => ipcRenderer.invoke("update:check"),
  restartToUpdate: () => ipcRenderer.invoke("update:restart"),
  onUpdate: callback => { ipcRenderer.on("update:state", (_event, state) => callback(state)); },
});
