import fs from "fs";
import os from "os";
import path from "path";

let initialized = false;
let logFilePath = "";

function resolveLogDir(): string {
    if (process.env.LOCALAPPDATA) {
        return path.join(process.env.LOCALAPPDATA, "justfit", "logs");
    }

    return path.join(os.homedir(), "AppData", "Local", "justfit", "logs");
}

function writeLog(level: string, args: unknown[]): void {
    if (!logFilePath) {
        return;
    }

    const timestamp = new Date().toISOString();
    const message = args
        .map((arg) => {
            if (arg instanceof Error) {
                return `${arg.name}: ${arg.message}\n${arg.stack ?? ""}`;
            }

            if (typeof arg === "string") {
                return arg;
            }

            try {
                return JSON.stringify(arg);
            } catch {
                return String(arg);
            }
        })
        .join(" ");

    fs.appendFileSync(logFilePath, `${timestamp} [${level}] ${message}\n`, "utf8");
}

export function initElectronLogging(): string {
    if (initialized) {
        return logFilePath;
    }

    const logDir = resolveLogDir();
    fs.mkdirSync(logDir, { recursive: true });
    logFilePath = path.join(logDir, "electron-main.log");

    const originalConsole = {
        log: console.log.bind(console),
        info: console.info.bind(console),
        warn: console.warn.bind(console),
        error: console.error.bind(console),
    };

    console.log = (...args: unknown[]) => {
        originalConsole.log(...args);
        writeLog("INFO", args);
    };

    console.info = (...args: unknown[]) => {
        originalConsole.info(...args);
        writeLog("INFO", args);
    };

    console.warn = (...args: unknown[]) => {
        originalConsole.warn(...args);
        writeLog("WARN", args);
    };

    console.error = (...args: unknown[]) => {
        originalConsole.error(...args);
        writeLog("ERROR", args);
    };

    initialized = true;
    console.log(`[Electron] Main log file: ${logFilePath}`);
    return logFilePath;
}

export function getElectronLogFilePath(): string {
    return logFilePath || path.join(resolveLogDir(), "electron-main.log");
}