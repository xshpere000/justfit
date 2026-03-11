/**
 * Electron Main Process Entry Point
 */

import { app, ipcMain, Menu } from "electron";
import { backendManager } from "./backend.js";
import { createMainWindow, getMainWindow, toggleMaximize, minimizeWindow } from "./window.js";
import { createTray, destroyTray } from "./tray.js";

/**
 * App lifecycle handlers
 */

app.whenReady().then(() => {
    Menu.setApplicationMenu(null);

    // Create main window
    createMainWindow();

    // Start Python backend
    backendManager.start();

    // Create system tray
    createTray();

    // Handle activate (especially for macOS)
    app.on("activate", () => {
        if (!getMainWindow()) {
            createMainWindow();
        }
    });
});

app.on("window-all-closed", () => {
    // On macOS, keep app running when all windows are closed
    if (process.platform !== "darwin") {
        app.quit();
    }
});

app.on("before-quit", () => {
    // Stop backend gracefully before quit
    backendManager.stop(true);
    destroyTray();
});

/**
 * IPC handlers
 */

// Window controls
ipcMain.handle("window:minimize", () => {
    minimizeWindow();
});

ipcMain.handle("window:maximize", () => {
    toggleMaximize();
});

ipcMain.handle("window:close", () => {
    const mainWindow = getMainWindow();
    mainWindow?.close();
});

ipcMain.handle("window:is-maximized", () => {
    const mainWindow = getMainWindow();
    return mainWindow?.isMaximized() ?? false;
});

// App info
ipcMain.handle("app:get-version", () => {
    return app.getVersion();
});

ipcMain.handle("app:get-data-path", () => {
    return app.getPath("userData");
});

// Backend control
ipcMain.handle("backend:get-url", () => {
    return "http://localhost:22631";
});

ipcMain.handle("backend:get-status", () => {
    return backendManager.getStatus();
});

ipcMain.handle("backend:restart", () => {
    backendManager.restart();
    return { success: true };
});

ipcMain.handle("backend:stop", () => {
    backendManager.stop();
    return { success: true };
});

ipcMain.handle("backend:start", () => {
    backendManager.start();
    return { success: true };
});
