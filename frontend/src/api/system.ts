/**
 * System API
 * System information and health endpoints
 */

import { apiClient } from "./client";

// Types
export interface SystemHealth {
    status: "healthy" | "unhealthy" | "degraded";
    version: string;
    database: "connected" | "disconnected";
    timestamp: string;
}

export interface SystemVersion {
    version: string;
    buildDate: string;
    gitCommit?: string;
}

export interface SystemStats {
    totalConnections: number;
    activeConnections: number;
    totalTasks: number;
    runningTasks: number;
    totalVMs: number;
}

/**
 * Get system health
 */
export async function getSystemHealth(): Promise<SystemHealth> {
    const response = await apiClient.get("/api/system/health");
    return response.data;
}

/**
 * Get system version
 */
export async function getSystemVersion(): Promise<SystemVersion> {
    const response = await apiClient.get("/api/system/version");
    return response.data;
}

/**
 * Get system statistics
 */
export async function getSystemStats(): Promise<SystemStats> {
    const response = await apiClient.get("/api/system/stats");
    return response.data;
}
