/**
 * Python Backend Process Management
 * Handles spawning, health checks, auto-restart, and graceful shutdown
 */

import { spawn, ChildProcess } from "child_process";
import { app } from "electron";
import path from "path";
import fs from "fs";

const PYTHON_PORT = 22631;
const HEALTH_CHECK_URL = `http://localhost:${PYTHON_PORT}/api/system/health`;
const HEALTH_CHECK_INTERVAL = 5000; // 5 seconds

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

    /**
     * Get backend directory path
     */
    private getBackendPath(): string {
        return path.join(__dirname, "../backend");
    }

    /**
     * Get Python executable path
     */
    private getPythonExe(): string {
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
     * Start the Python backend
     */
    start(): ChildProcess {
        if (this.process) {
            console.log("[Backend] Already running");
            return this.process;
        }

        const pythonExe = this.getPythonExe();
        const backendPath = this.getBackendPath();

        console.log(`[Backend] Starting with: ${pythonExe}`);

        this.process = spawn(pythonExe, [
            "-m", "uvicorn",
            "app.main:app",
            "--port", String(PYTHON_PORT),
            "--host", "127.0.0.1",
        ], {
            cwd: backendPath,
            env: {
                ...process.env,
                PYTHONUNBUFFERED: "1",
                JUSTFIT_DATA_DIR: path.join(app.getPath("userData"), "data"),
            },
        });

        this.startTime = Date.now();

        // Log output
        this.process.stdout?.on("data", (data) => {
            console.log(`[Python] ${data.toString().trim()}`);
        });

        this.process.stderr?.on("data", (data) => {
            console.error(`[Python Error] ${data.toString().trim()}`);
        });

        this.process.on("error", (err) => {
            console.error(`[Backend] Failed to start: ${err.message}`);
        });

        this.process.on("exit", (code, signal) => {
            console.log(`[Backend] Exited: code=${code}, signal=${signal}`);
            this.stopHealthCheck();
            this.process = null;
        });

        // Start health check
        this.startHealthCheck();

        return this.process;
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
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 3000);

            const response = await fetch(HEALTH_CHECK_URL, {
                signal: controller.signal,
            });

            clearTimeout(timeout);

            if (response.ok) {
                this.unhealthyCount = 0;
            } else {
                this.unhealthyCount++;
            }
        } catch (err) {
            this.unhealthyCount++;
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
