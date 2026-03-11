/**
 * Report API
 * Report generation endpoints
 */

import { apiClient } from "./client";

// Types
export type ReportFormat = "excel" | "pdf";

export interface ReportRequest {
    format: ReportFormat;
    includeRawData?: boolean;
}

export interface Report {
    id: number;
    taskId: number;
    format: ReportFormat;
    filePath: string;
    fileSize: number;
    createdAt: string;
}

export interface ReportGenerateResponse {
    reportId: number;
    downloadUrl: string;
}

/**
 * Generate report for a task
 */
export async function generateReport(taskId: number, request: ReportRequest): Promise<ReportGenerateResponse> {
    const response = await apiClient.post(`/api/reports/tasks/${taskId}/reports`, request);
    return response.data.data;
}

/**
 * Get report download URL
 */
export function getReportDownloadUrl(reportId: number): string {
    return `/api/reports/${reportId}/download`;
}

/**
 * Download report
 */
export async function downloadReport(reportId: number): Promise<Blob> {
    const response = await apiClient.get(`/api/reports/${reportId}/download`, {
        responseType: "blob",
    });
    return response.data;
}

/**
 * Get reports for a task
 */
export async function getTaskReports(taskId: number): Promise<Report[]> {
    const response = await apiClient.get(`/api/reports/tasks/${taskId}/reports`);
    return response.data.data;
}

/**
 * Delete report
 */
export async function deleteReport(reportId: number): Promise<void> {
    await apiClient.delete(`/api/reports/${reportId}`);
}

/**
 * Download blob helper (for frontend file download)
 */
export function downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Download report by ID (triggers browser download)
 */
export async function downloadReportFile(reportId: number, filename: string): Promise<void> {
    const blob = await downloadReport(reportId);
    downloadBlob(blob, filename);
}

/**
 * Export task report (legacy API compatibility)
 */
export async function exportTaskReport(params: {
    taskId: string;
    connectionId: number;
    reportTypes: string[];
    title: string;
}): Promise<void> {
    const taskId = parseInt(params.taskId);
    const format = params.reportTypes[0] === "xlsx" ? "excel" : "pdf";
    await generateReport(taskId, { format });
}
