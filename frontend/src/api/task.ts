/**
 * Task API
 * Task management endpoints
 */

import { apiClient } from "./client";

// Types
export type TaskType = "collection" | "analysis";
export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface Task {
    id: number;
    type: TaskType;
    name: string;
    status: TaskStatus;
    progress: number;
    error: string | null;
    connectionId: number | null;
    currentStep: string;
    analysisResults: {
        zombie: boolean;
        rightsize: boolean;
        tidal: boolean;
        health: boolean;
    };
    createdAt: string;
    startedAt: string | null;
    completedAt: string | null;
    // 详情接口额外字段（可选）
    platform?: string;
    connectionName?: string;
    connectionHost?: string;
    selectedVMCount?: number;
    collectedVMCount?: number;
    selectedVMs?: string[];
    config?: Record<string, unknown>;
}

export interface TaskCreate {
    type: TaskType;
    name: string;
    connectionId?: number;
    config?: Record<string, unknown>;
}

export interface TaskDetail extends Task {
    connection?: {
        id: number;
        name: string;
        platform: string;
    };
    vmSnapshots: TaskVMSnapshot[];
    analysisJobs: TaskAnalysisJob[];
    findings: AnalysisFinding[];
    reports: TaskReport[];
    logs: TaskLog[];
}

export interface TaskVMSnapshot {
    id: number;
    taskId: number;
    vmName: string;
    vmKey: string;
    datacenter: string;
    cpuCount: number;
    memoryBytes: number;
    powerState: string;
    hostIp: string;
}

export interface TaskAnalysisJob {
    id: number;
    taskId: number;
    jobType: "zombie" | "rightsize" | "tidal" | "health";
    status: TaskStatus;
    startedAt: string | null;
    completedAt: string | null;
    config: string | null;
    resultSummary: string | null;
    error: string | null;
}

export interface AnalysisFinding {
    id: number;
    taskId: number;
    jobId: number;
    jobType: string;
    vmName: string;
    severity: "info" | "low" | "medium" | "high" | "critical";
    title: string;
    description: string;
    recommendation: string;
    details: string | null;
    estimatedSaving: string | null;
    confidence: number;
    createdAt: string;
}

export interface TaskReport {
    id: number;
    taskId: number;
    format: "excel" | "pdf";
    filePath: string;
    fileSize: number;
    createdAt: string;
}

export interface TaskLog {
    id: number;
    taskId: number;
    level: "debug" | "info" | "warn" | "error";
    message: string;
    createdAt: string;
}

export interface TaskListResponse {
    items: Task[];
    total: number;
}

/**
 * List tasks
 */
export async function listTasks(params?: {
    type?: TaskType;
    status?: TaskStatus;
    page?: number;
    size?: number;
}): Promise<TaskListResponse> {
    const response = await apiClient.get("/api/tasks", { params });
    return response.data.data;
}

/**
 * Get task by ID
 */
export async function getTask(id: number): Promise<Task> {
    const response = await apiClient.get(`/api/tasks/${id}`);
    return response.data.data;
}

/**
 * Get task detail (same as getTask, uses the same backend endpoint)
 */
export async function getTaskDetail(id: number): Promise<TaskDetail> {
    const response = await apiClient.get(`/api/tasks/${id}`);
    return response.data.data;
}

/**
 * Create task
 */
export async function createTask(data: TaskCreate): Promise<Task> {
    const response = await apiClient.post("/api/tasks", data);
    return response.data.data;
}

/**
 * Cancel task
 */
export async function cancelTask(id: number): Promise<void> {
    await apiClient.post(`/api/tasks/${id}/cancel`);
}

/**
 * Delete task
 */
export async function deleteTask(id: number): Promise<void> {
    await apiClient.delete(`/api/tasks/${id}`);
}

/**
 * Get task logs
 */
export async function getTaskLogs(id: number): Promise<TaskLog[]> {
    const response = await apiClient.get(`/api/tasks/${id}/logs`);
    return response.data.data.items;
}

/**
 * Get task VM snapshots
 */
export async function getTaskVMSnapshots(id: number): Promise<TaskVMSnapshot[]> {
    const response = await apiClient.get(`/api/tasks/${id}/vm-snapshots`);
    return response.data.data;
}

/**
 * List task VMs with pagination
 */
export async function listTaskVMs(
    taskId: number,
    limit: number = 50,
    offset: number = 0,
    keyword: string = ""
): Promise<{ vms: TaskVMSnapshot[]; total: number }> {
    const response = await apiClient.get(`/api/tasks/${taskId}/vms`, {
        params: { limit, offset, keyword },
    });
    return response.data.data;
}

/**
 * Retry a failed task
 */
export async function retryTask(taskId: number): Promise<number> {
    const response = await apiClient.post(`/api/tasks/${taskId}/retry`);
    return response.data.data.taskId;
}
