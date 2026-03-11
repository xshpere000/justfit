/**
 * Window Management
 * Creates and manages the main application window
 */

import { BrowserWindow, app } from "electron";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: BrowserWindow | null = null;

/**
 * Create the main browser window
 */
export function createMainWindow(): BrowserWindow {
    if (mainWindow) {
        mainWindow.focus();
        return mainWindow;
    }

    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        backgroundColor: "#f5f5f5",
        show: false, // Show when ready
        autoHideMenuBar: true,
        titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
        frame: true,
        webPreferences: {
            preload: path.join(__dirname, "preload.cjs"),
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true,
        },
    });

    mainWindow.setMenuBarVisibility(false);

    // Load content
    const isDev = !app.isPackaged;
    if (isDev) {
        mainWindow.loadURL("http://localhost:22632");
        mainWindow.webContents.openDevTools();
    } else {
        const packagedIndexPath = path.join(process.resourcesPath, "frontend", "dist", "index.html");
        console.log("[Window] Loading packaged index", { packagedIndexPath, exists: fs.existsSync(packagedIndexPath) });
        mainWindow.loadFile(packagedIndexPath);
    }

    mainWindow.webContents.on("did-finish-load", () => {
        console.log("[Window] Renderer finished load");
    });

    mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
        console.error("[Window] Failed to load:", {
            errorCode,
            errorDescription,
            validatedURL,
        });
        mainWindow?.show();
    });

    mainWindow.webContents.on("render-process-gone", (_event, details) => {
        console.error("[Window] Renderer process gone", details);
    });

    mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
        if (level >= 2) {
            console.warn("[Renderer] Console message", { level, message, line, sourceId });
        }
    });

    // Handle window events
    mainWindow.once("ready-to-show", () => {
        mainWindow?.show();
    });

    mainWindow.on("closed", () => {
        mainWindow = null;
    });

    // Prevent navigation to external URLs
    mainWindow.webContents.on("will-navigate", (event, url) => {
        const allowedOrigins = [
            "http://localhost:22632",
            "http://localhost:22631",
        ];
        const urlObj = new URL(url);
        if (!allowedOrigins.includes(urlObj.origin)) {
            event.preventDefault();
        }
    });

    return mainWindow;
}

/**
 * Get the main window
 */
export function getMainWindow(): BrowserWindow | null {
    return mainWindow;
}

/**
 * Close the main window
 */
export function closeMainWindow(): void {
    if (mainWindow) {
        mainWindow.close();
        mainWindow = null;
    }
}

/**
 * Toggle window maximize state
 */
export function toggleMaximize(): void {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
}

/**
 * Minimize the main window
 */
export function minimizeWindow(): void {
    mainWindow?.minimize();
}

/**
 * Check if window is maximized
 */
export function isMaximized(): boolean {
    return mainWindow?.isMaximized() ?? false;
}
