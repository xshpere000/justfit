/**
 * Electron Preload Script
 * Exposes safe IPC channels to renderer process
 */

import { contextBridge, ipcRenderer } from "electron";

const electronAPI = {
    minimize: () => ipcRenderer.invoke("window:minimize"),
    toggleMaximize: () => ipcRenderer.invoke("window:maximize"),
    close: () => ipcRenderer.invoke("window:close"),
    isMaximized: () => ipcRenderer.invoke("window:is-maximized"),
    windowMinimize: () => ipcRenderer.invoke("window:minimize"),
    windowMaximize: () => ipcRenderer.invoke("window:maximize"),
    windowClose: () => ipcRenderer.invoke("window:close"),
    windowIsMaximized: () => ipcRenderer.invoke("window:is-maximized"),
    getVersion: () => ipcRenderer.invoke("app:get-version"),
    getDataPath: () => ipcRenderer.invoke("app:get-data-path"),
    getBackendUrl: () => ipcRenderer.invoke("backend:get-url"),
    getBackendStatus: () => ipcRenderer.invoke("backend:get-status"),
    restartBackend: () => ipcRenderer.invoke("backend:restart"),
    stopBackend: () => ipcRenderer.invoke("backend:stop"),
    startBackend: () => ipcRenderer.invoke("backend:start"),
};

contextBridge.exposeInMainWorld("electronAPI", electronAPI);

export type ElectronAPI = typeof electronAPI;

declare global {
    interface Window {
        electronAPI: ElectronAPI;
    }
}