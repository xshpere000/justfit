/**
 * Window Management
 * Creates and manages the main application window
 */

import { BrowserWindow, app } from "electron";
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
        titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
        frame: true,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: true,
        },
    });

    // Load content
    const isDev = process.env.NODE_ENV === "development";
    if (isDev) {
        mainWindow.loadURL("http://localhost:22632");
        mainWindow.webContents.openDevTools();
    } else {
        mainWindow.loadFile(path.join(__dirname, "../frontend/dist/index.html"));
    }

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
