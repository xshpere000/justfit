/**
 * System Tray
 * Manages the application's system tray icon and menu
 */

import { Tray, Menu, app, nativeImage } from "electron";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getMainWindow } from "./window.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let tray: Tray | null = null;

/**
 * Create the system tray
 */
export function createTray(): Tray | null {
    if (tray) {
        return tray;
    }

    const iconPath = getTrayIconPath();
    if (!fs.existsSync(iconPath)) {
        console.warn("[Tray] Icon not found, tray disabled", { iconPath });
        return null;
    }

    const icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) {
        console.warn("[Tray] Icon file is invalid, tray disabled", { iconPath });
        return null;
    }

    tray = new Tray(icon);

    // Set tooltip
    tray.setToolTip("JustFit - Cloud Platform Resource Assessment");

    // Create context menu
    const contextMenu = Menu.buildFromTemplate([
        {
            label: "Show JustFit",
            click: () => {
                // Focus main window
                const windows = getMainWindow();
                if (windows) {
                    windows.show();
                    windows.focus();
                }
            },
        },
        { type: "separator" },
        {
            label: "Backend Status",
            click: () => {
                // Could show status dialog
                console.log("Backend status checked");
            },
        },
        { type: "separator" },
        {
            label: "Quit JustFit",
            click: () => {
                app.quit();
            },
        },
    ]);

    tray.setContextMenu(contextMenu);

    // Handle double-click to show window
    tray.on("double-click", () => {
        const mainWindow = getMainWindow();
        if (mainWindow) {
            if (mainWindow.isMinimized()) {
                mainWindow.restore();
            }
            mainWindow.show();
            mainWindow.focus();
        }
    });

    return tray;
}

/**
 * Get tray icon path based on platform
 */
function getTrayIconPath(): string {
    const iconDir = app.isPackaged
        ? path.join(process.resourcesPath, "icons")
        : path.resolve(__dirname, "..", "resources", "icons");

    const fallbackIcon = process.platform === "win32"
        ? path.join(iconDir, "icon.ico")
        : path.join(iconDir, "app.png");

    switch (process.platform) {
        case "darwin":
            return fs.existsSync(path.join(iconDir, "tray", "iconTemplate.png"))
                ? path.join(iconDir, "tray", "iconTemplate.png")
                : fallbackIcon;
        case "win32":
            return fs.existsSync(path.join(iconDir, "tray", "icon.ico"))
                ? path.join(iconDir, "tray", "icon.ico")
                : fallbackIcon;
        default:
            return fs.existsSync(path.join(iconDir, "tray", "icon.png"))
                ? path.join(iconDir, "tray", "icon.png")
                : fallbackIcon;
    }
}

/**
 * Update tray icon based on backend status
 */
export function updateTrayIcon(backendHealthy: boolean): void {
    if (!tray) return;

    const iconDir = app.isPackaged
        ? path.join(process.resourcesPath, "icons")
        : path.resolve(__dirname, "..", "resources", "icons");
    const iconName = backendHealthy ? "icon" : "icon-warning";
    const ext = process.platform === "win32" ? "ico" : "png";

    try {
        const iconPath = path.join(iconDir, "tray", `${iconName}.${ext}`);
        const resolvedPath = fs.existsSync(iconPath)
            ? iconPath
            : (process.platform === "win32" ? path.join(iconDir, "icon.ico") : path.join(iconDir, "app.png"));
        const icon = nativeImage.createFromPath(resolvedPath);
        if (icon.isEmpty()) {
            console.warn("[Tray] Failed to load tray icon", { resolvedPath });
            return;
        }
        tray.setImage(icon);
    } catch (err) {
        console.warn("Failed to update tray icon:", err);
    }
}

/**
 * Destroy the tray
 */
export function destroyTray(): void {
    if (tray) {
        tray.destroy();
        tray = null;
    }
}
