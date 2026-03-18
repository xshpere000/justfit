/**
 * Electron Main Process Entry Point
 */

import { app, ipcMain, Menu, globalShortcut, dialog } from "electron";
import { backendManager } from "./backend.js";
import { createMainWindow, getMainWindow, setCloseRequestHandler, toggleMaximize, minimizeWindow } from "./window.js";
import { createTray, destroyTray } from "./tray.js";
import { getElectronLogFilePath, initElectronLogging } from "./logger.js";

initElectronLogging();

process.on("uncaughtException", (error) => {
    console.error("[Electron] Uncaught exception", error);
});

process.on("unhandledRejection", (reason) => {
    console.error("[Electron] Unhandled rejection", reason);
});

/**
 * Single instance lock - prevent multiple app instances
 */
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    console.log("[Electron] Another instance is already running, quitting");
    app.quit();
    process.exit(0);
}

app.on("second-instance", () => {
    // When a second instance tries to launch, focus the existing window and notify user
    const mainWindow = getMainWindow();
    if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
    }
    dialog.showMessageBox({
        type: "warning",
        title: "JustFit 已在运行",
        message: "JustFit 已经在运行中，不允许重复启动。",
        detail: "请切换到已打开的 JustFit 窗口继续使用。",
        buttons: ["确定"],
        defaultId: 0,
    });
});

/**
 * App lifecycle handlers
 */

app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    console.log("[Electron] App ready", {
        isPackaged: app.isPackaged,
        userData: app.getPath("userData"),
        logs: getElectronLogFilePath(),
    });

    // Start Python backend
    try {
        backendManager.start();
    } catch (error) {
        console.error("[Electron] Failed to start backend manager", error);
    }

    // Register close handler BEFORE creating window
    setCloseRequestHandler(() => handleQuit());

    // Create main window (show=false until both renderer and backend are ready)
    const win = createMainWindow();

    // Show window only when both renderer is ready AND backend is healthy
    Promise.all([
        new Promise<void>((resolve) => win.once("ready-to-show", resolve)),
        backendManager.waitUntilHealthy(60000).then((healthy) => {
            if (!healthy) {
                console.warn("[Electron] Backend did not become healthy in time, showing window anyway");
            } else {
                console.log("[Electron] Backend is healthy");
            }
        }),
    ]).then(() => {
        console.log("[Electron] Window and backend ready, showing window");
        win.show();
    });

    // Create system tray
    try {
        createTray();
    } catch (error) {
        console.error("[Electron] Failed to create tray", error);
    }

    // Register global shortcuts
    globalShortcut.register("F12", () => {
        getMainWindow()?.webContents.toggleDevTools();
    });
    globalShortcut.register("F5", () => {
        getMainWindow()?.webContents.reload();
    });
    globalShortcut.register("Shift+F5", () => {
        getMainWindow()?.webContents.reloadIgnoringCache();
    });

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

let isQuitting = false;

/**
 * Graceful shutdown with fallback force-kill dialog.
 * Called from the window 'close' event (preventDefault keeps window visible).
 */
async function handleQuit(): Promise<void> {
    if (isQuitting) return;
    isQuitting = true;

    const mainWindow = getMainWindow();

    // Show "closing" state in title to give user feedback
    mainWindow?.setTitle("JustFit - 正在关闭...");
    mainWindow?.webContents.executeJavaScript(
        `document.body.style.pointerEvents='none'; document.body.style.opacity='0.6';`
    ).catch(() => {});

    destroyTray();
    globalShortcut.unregisterAll();

    const backendStopped = await Promise.race([
        backendManager.stopAndWait(true).then(() => true),
        new Promise<false>((resolve) => setTimeout(() => resolve(false), 6000)),
    ]);

    if (backendStopped) {
        // Backend stopped cleanly — destroy window and exit
        mainWindow?.destroy();
        app.exit(0);
        return;
    }

    // Backend failed to stop in time — ask user
    const { response } = await dialog.showMessageBox({
        type: "error",
        title: "后端未能正常关闭",
        message: "后端进程未能在规定时间内停止。",
        detail: "请选择操作：\n> 强制关闭：立即终止所有进程并退出（推荐）\n> 取消：返回应用，稍后再试",
        buttons: ["强制关闭", "取消"],
        defaultId: 0,
        cancelId: 1,
    });

    if (response === 0) {
        // Nuclear option: force-kill backend then hard-exit
        backendManager.forceKillNow();
        mainWindow?.destroy();
        app.exit(0);
    } else {
        // User cancelled — restore window to usable state
        isQuitting = false;
        mainWindow?.setTitle("JustFit");
        mainWindow?.webContents.executeJavaScript(
            `document.body.style.pointerEvents=''; document.body.style.opacity='';`
        ).catch(() => {});
    }
}

// will-quit fires if something else calls app.quit() directly (e.g. tray menu)
app.on("will-quit", (event) => {
    if (!isQuitting) {
        event.preventDefault();
        handleQuit();
    }
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

ipcMain.handle("app:get-log-path", () => {
    return getElectronLogFilePath();
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
