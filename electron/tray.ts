/**
 * System Tray
 * Manages the application's system tray icon and menu
 */

import { Tray, Menu, app, nativeImage } from "electron";
import path from "path";

let tray: Tray | null = null;

/**
 * Create the system tray
 */
export function createTray(): Tray | null {
    if (tray) {
        return tray;
    }

    // Create tray icon (use default icon for now, should be replaced with actual icon)
    const iconPath = getTrayIconPath();
    const icon = nativeImage.createFromPath(iconPath);

    tray = new Tray(icon);

    // Set tooltip
    tray.setToolTip("JustFit - Cloud Platform Resource Assessment");

    // Create context menu
    const contextMenu = Menu.buildFromTemplate([
        {
            label: "Show JustFit",
            click: () => {
                // Focus main window
                const windows = require("./window").getMainWindow();
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
        const { getMainWindow } = require("./window");
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
    // For now, return a placeholder path
    // In production, this should point to actual icon files
    const iconDir = path.join(__dirname, "../resources/icons");

    switch (process.platform) {
        case "darwin":
            return path.join(iconDir, "tray", "iconTemplate.png");
        case "win32":
            return path.join(iconDir, "tray", "icon.ico");
        default:
            return path.join(iconDir, "tray", "icon.png");
    }
}

/**
 * Update tray icon based on backend status
 */
export function updateTrayIcon(backendHealthy: boolean): void {
    if (!tray) return;

    const iconDir = path.join(__dirname, "../resources/icons");
    const iconName = backendHealthy ? "icon" : "icon-warning";
    const ext = process.platform === "win32" ? "ico" : "png";

    try {
        const iconPath = path.join(iconDir, "tray", `${iconName}.${ext}`);
        const icon = nativeImage.createFromPath(iconPath);
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
