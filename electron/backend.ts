/**
 * Python Backend Process Management
 * Handles spawning, health checks, auto-restart, and graceful shutdown
 */

import { spawn, ChildProcess } from "child_process";
import { app } from "electron";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const PYTHON_PORT = 22631;
const HEALTH_CHECK_URL = `http://localhost:${PYTHON_PORT}/api/system/health`;
const HEALTH_CHECK_INTERVAL = 5000; // 5 seconds
const PACKAGED_STARTUP_GRACE_MS = 60000;
const DEV_STARTUP_GRACE_MS = 10000;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export interface BackendStatus {
    running: boolean;
    healthy: boolean;
    pid?: number;
    uptime?: number;
    lastError?: string;
}

/**
 * Backend Process Manager
 */
export class BackendManager {
    private process: ChildProcess | null = null;
    private startTime: number = 0;
    private healthCheckTimer: NodeJS.Timeout | null = null;
    private unhealthyCount: number = 0;
    private readonly MAX_UNHEALTHY = 3;
    private hasBeenHealthy: boolean = false;
    private lastError?: string;

    private getPackagedBackendExe(): string {
        return path.join(process.resourcesPath, "backend", "justfit_backend.exe");
    }

    private getDevPackagedBackendExe(): string {
        return path.resolve(__dirname, "..", "..", "resources", "backend", "justfit_backend.exe");
    }

    /**
     * Get backend directory path
     */
    private getBackendPath(): string {
        return path.resolve(__dirname, "..", "..", "backend");
    }

    /**
     * Get Python executable path
     * 优先使用打包好的 exe，否则使用系统 Python
     */
    private getPythonExe(): string {
        // 1. 检查是否有打包好的后端 exe（生产环境）
        const isPackaged = app.isPackaged;
        if (isPackaged) {
            const backendExe = this.getPackagedBackendExe();
            if (fs.existsSync(backendExe)) {
                console.log("[Backend] Using packaged backend exe");
                return backendExe;
            }
        }

        // 2. 检查开发环境中的打包 exe
        const devBackendExe = this.getDevPackagedBackendExe();
        if (fs.existsSync(devBackendExe)) {
            console.log("[Backend] Using dev packaged backend exe");
            return devBackendExe;
        }

        // 3. 回退到使用 Python 解释器
        const backendPath = this.getBackendPath();
        const venvPath = path.join(backendPath, ".venv");

        let pythonExe = process.platform === "win32"
            ? path.join(venvPath, "Scripts", "python.exe")
            : path.join(venvPath, "bin", "python");

        if (!fs.existsSync(pythonExe)) {
            pythonExe = "python3.14";
        }

        return pythonExe;
    }

    /**
     * 检查是否使用打包好的 exe
     */
    private usePackagedExe(): boolean {
        const exePath = this.getPythonExe();
        return exePath.endsWith("justfit_backend.exe") && fs.existsSync(exePath);
    }

    /**
     * Start the Python backend
     */
    start(): ChildProcess {
        if (this.process) {
            console.log("[Backend] Already running");
            return this.process;
        }

        const pythonExe = this.getPythonExe();
        const useExe = this.usePackagedExe();
        const backendPath = this.getBackendPath();
        const exeExists = fs.existsSync(pythonExe);

        this.hasBeenHealthy = false;
        this.lastError = undefined;

        console.log(`[Backend] Starting with: ${pythonExe}`);
        console.log(`[Backend] Mode: ${useExe ? "Packaged EXE" : "Python + Uvicorn"}`);
        console.log("[Backend] Start context", {
            exeExists,
            isPackaged: app.isPackaged,
            resourcesPath: process.resourcesPath,
            backendPath,
        });

        let args: string[];
        let cwd: string;

        if (useExe) {
            // 使用打包好的 exe，直接运行，不需要额外参数
            args = [];
            cwd = path.dirname(pythonExe);
        } else {
            // 使用 Python + uvicorn
            args = [
                "-m", "uvicorn",
                "app.main:app",
                "--port", String(PYTHON_PORT),
                "--host", "127.0.0.1",
            ];
            cwd = backendPath;
        }

        this.process = spawn(pythonExe, args, {
            cwd,
            env: {
                ...process.env,
                PYTHONUNBUFFERED: "1",
            },
            windowsHide: true,
        });

        this.startTime = Date.now();

        // Log output
        this.process.stdout?.on("data", (data) => {
            console.log(`[Python] ${data.toString().trim()}`);
        });

        this.process.stderr?.on("data", (data) => {
            this.lastError = data.toString().trim();
            console.error(`[Python Error] ${this.lastError}`);
        });

        this.process.on("error", (err) => {
            this.lastError = err.message;
            console.error(`[Backend] Failed to start: ${err.message}`);
        });

        this.process.on("exit", (code, signal) => {
            if (code !== 0) {
                this.lastError = `Backend exited with code=${code}, signal=${signal}`;
            }
            console.log(`[Backend] Exited: code=${code}, signal=${signal}`);
            this.stopHealthCheck();
            this.process = null;
        });

        // Start health check
        this.startHealthCheck();

        return this.process;
    }

    /**
     * Stop the Python backend and wait for it to exit
     */
    stopAndWait(graceful = true): Promise<void> {
        return new Promise((resolve) => {
            if (!this.process) {
                resolve();
                return;
            }

            this.stopHealthCheck();

            // Force kill after timeout regardless
            const forceKillTimer = setTimeout(() => {
                if (this.process) {
                    console.log("[Backend] Force kill after timeout");
                    this.process.kill("SIGKILL");
                }
                resolve();
            }, 5000);

            this.process.once("exit", () => {
                clearTimeout(forceKillTimer);
                resolve();
            });

            if (graceful) {
                console.log("[Backend] Stopping gracefully...");
                this.process.kill("SIGTERM");
            } else {
                console.log("[Backend] Stopping forcefully...");
                this.process.kill("SIGKILL");
            }
        });
    }

    /**
     * Stop the Python backend
     */
    stop(graceful = true): void {
        if (!this.process) {
            return;
        }

        this.stopHealthCheck();

        if (graceful) {
            console.log("[Backend] Stopping gracefully...");
            this.process.kill("SIGTERM");
        } else {
            console.log("[Backend] Stopping forcefully...");
            this.process.kill("SIGKILL");
        }

        // Force kill after timeout
        setTimeout(() => {
            if (this.process) {
                console.log("[Backend] Force kill after timeout");
                this.process.kill("SIGKILL");
            }
        }, 5000);
    }

    /**
     * Restart the backend
     */
    restart(): void {
        console.log("[Backend] Restarting...");
        this.stop();
        setTimeout(() => this.start(), 1000);
    }

    /**
     * Get current status
     */
    getStatus(): BackendStatus {
        const running = this.process !== null && !this.process.killed;
        return {
            running,
            healthy: running && this.unhealthyCount < this.MAX_UNHEALTHY,
            pid: this.process?.pid,
            uptime: running ? Date.now() - this.startTime : 0,
            lastError: this.lastError,
        };
    }

    /**
     * Start health check loop
     */
    private startHealthCheck(): void {
        this.healthCheckTimer = setInterval(() => {
            this.checkHealth();
        }, HEALTH_CHECK_INTERVAL);

        // Initial check after a short delay
        setTimeout(() => this.checkHealth(), 2000);
    }

    /**
     * Stop health check loop
     */
    private stopHealthCheck(): void {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
            this.healthCheckTimer = null;
        }
        this.unhealthyCount = 0;
    }

    /**
     * Check backend health via HTTP
     */
    private async checkHealth(): Promise<void> {
        const startupGraceMs = this.usePackagedExe() ? PACKAGED_STARTUP_GRACE_MS : DEV_STARTUP_GRACE_MS;
        const isInStartupGracePeriod = !this.hasBeenHealthy && Date.now() - this.startTime < startupGraceMs;

        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 3000);

            const response = await fetch(HEALTH_CHECK_URL, {
                signal: controller.signal,
            });

            clearTimeout(timeout);

            if (response.ok) {
                this.hasBeenHealthy = true;
                this.unhealthyCount = 0;
                this.lastError = undefined;
            } else {
                if (isInStartupGracePeriod) {
                    console.warn("[Backend] Health check not ready yet during startup grace period");
                    return;
                }
                this.unhealthyCount++;
            }
        } catch (err) {
            if (isInStartupGracePeriod) {
                console.warn(`[Backend] Waiting for startup during grace period: ${err}`);
                return;
            }

            this.unhealthyCount++;
            this.lastError = String(err);
            console.warn(`[Backend] Health check failed: ${err}`);

            // Auto-restart if unhealthy for too long
            if (this.unhealthyCount >= this.MAX_UNHEALTHY) {
                console.error("[Backend] Too many unhealthy checks, restarting...");
                this.restart();
            }
        }
    }
}

// Singleton instance
export const backendManager = new BackendManager();
