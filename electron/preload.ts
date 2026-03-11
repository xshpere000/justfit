/**
 * Electron Preload Script
 * Exposes safe IPC channels to renderer process
 */

import { contextBridge, ipcRenderer } from "electron";

/**
 * Electron API interface exposed to renderer
 */
const electronAPI = {
    // Window controls
    minimize: () => ipcRenderer.invoke("window:minimize"),
    toggleMaximize: () => ipcRenderer.invoke("window:maximize"),
    close: () => ipcRenderer.invoke("window:close"),
    isMaximized: () => ipcRenderer.invoke("window:is-maximized"),
    windowMinimize: () => ipcRenderer.invoke("window:minimize"),
    windowMaximize: () => ipcRenderer.invoke("window:maximize"),
    windowClose: () => ipcRenderer.invoke("window:close"),
    windowIsMaximized: () => ipcRenderer.invoke("window:is-maximized"),

    // App info
    getVersion: () => ipcRenderer.invoke("app:get-version"),
    getDataPath: () => ipcRenderer.invoke("app:get-data-path"),

    // Backend control
    getBackendUrl: () => ipcRenderer.invoke("backend:get-url"),
    getBackendStatus: () => ipcRenderer.invoke("backend:get-status"),
    restartBackend: () => ipcRenderer.invoke("backend:restart"),
    stopBackend: () => ipcRenderer.invoke("backend:stop"),
    startBackend: () => ipcRenderer.invoke("backend:start"),
};

// Expose API to renderer
contextBridge.exposeInMainWorld("electronAPI", electronAPI);

// Type definitions for TypeScript
export type ElectronAPI = typeof electronAPI;

// Extend global Window interface
declare global {
    interface Window {
        electronAPI: ElectronAPI;
    }
}
