/**
 * Analysis API
 * Analysis engine endpoints
 */

import { apiClient } from "./client";

// Types
export interface AnalysisModes {
    safe: AnalysisModeConfig;
    saving: AnalysisModeConfig;
    aggressive: AnalysisModeConfig;
    custom: AnalysisModeConfig;
}

export interface AnalysisModeConfig {
    zombie: {
        days: number;
        cpuThreshold: number;
        memoryThreshold: number;
        minConfidence: number;
    };
    rightsize: {
        days: number;
        bufferPercent: number;
        p95Threshold: number;
    };
    tidal: {
        days: number;
        minStability: number;
    };
}

export interface ZombieResult {
    vmName: string;
    cluster: string;
    hostIp: string;
    cpuCores: number;
    memoryGb: number;
    cpuUsage: number;
    memoryUsage: number;
    diskIoUsage: number;
    networkUsage: number;
    confidence: number;
    recommendation: string;
}

export interface RightSizeResult {
    vmName: string;
    cluster: string;
    currentCPU: number;
    suggestedCPU: number;
    currentMemory: number;
    suggestedMemory: number;
    adjustmentType: string;
    riskLevel: string;
    confidence: number;
    recommendation: string;
}

export interface TidalResult {
    vmName: string;
    cluster: string;
    patternType: string;
    stabilityScore: number;
    peakHours: number[];
    peakDays: number[];
    recommendation: string;
}

export interface HealthScoreResult {
    overallScore: number;
    level: string;
    balanceScore: number;
    overcommitScore: number;
    hotspotScore: number;
    risks: string[];
    recommendations: string[];
}

export interface AnalysisResult<T> {
    taskId: number;
    jobType: string;
    status: string;
    results: T[];
    summary: {
        total: number;
        critical: number;
        high: number;
        medium: number;
        low: number;
    };
}

/**
 * Get all analysis modes
 */
export async function getAnalysisModes(): Promise<AnalysisModes> {
    const response = await apiClient.get("/api/analysis/modes");
    return response.data.data;
}

/**
 * Get specific analysis mode
 */
export async function getAnalysisMode(mode: string): Promise<AnalysisModeConfig> {
    const response = await apiClient.get(`/api/analysis/modes/${mode}`);
    return response.data.data;
}

/**
 * Update custom mode
 */
export async function updateCustomMode(config: Partial<AnalysisModeConfig>): Promise<void> {
    await apiClient.put("/api/analysis/modes/custom", config);
}

/**
 * Get zombie analysis results
 */
export async function getZombieResults(taskId: number): Promise<AnalysisResult<ZombieResult>> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/zombie`);
    return response.data.data;
}

/**
 * Get rightsize analysis results
 */
export async function getRightSizeResults(taskId: number): Promise<AnalysisResult<RightSizeResult>> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/rightsize`);
    return response.data.data;
}

/**
 * Get tidal analysis results
 */
export async function getTidalResults(taskId: number): Promise<AnalysisResult<TidalResult>> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/tidal`);
    return response.data.data;
}

/**
 * Get health score results (based on task, like other analyses)
 */
export async function getHealthResults(taskId: number): Promise<AnalysisResult<HealthScoreResult>> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/health`);
    return response.data.data;
}

/**
 * Run zombie analysis
 */
export async function runZombieAnalysis(taskId: number, config?: Record<string, unknown>): Promise<void> {
    await apiClient.post(`/api/analysis/tasks/${taskId}/zombie`, config);
}

/**
 * Run rightsize analysis
 */
export async function runRightSizeAnalysis(taskId: number, config?: Record<string, unknown>): Promise<void> {
    await apiClient.post(`/api/analysis/tasks/${taskId}/rightsize`, config);
}

/**
 * Run tidal analysis
 */
export async function runTidalAnalysis(taskId: number, config?: Record<string, unknown>): Promise<void> {
    await apiClient.post(`/api/analysis/tasks/${taskId}/tidal`, config);
}

/**
 * Run health analysis (based on task, like other analyses)
 */
export async function runHealthAnalysis(taskId: number, config?: Record<string, unknown>): Promise<any> {
    const response = await apiClient.post(`/api/analysis/tasks/${taskId}/health`, config);
    return response.data.data;
}

/**
 * Get all analysis results for a task
 */
export async function getTaskAnalysisResult(
  taskId: number,
  analysisType?: string
): Promise<Record<string, unknown>> {
  // If specific type requested, fetch only that
  if (analysisType) {
    const url = `/api/analysis/tasks/${taskId}/${analysisType}`;
    const response = await apiClient.get(url);
    return response.data.data;
  }

  // Fetch zombie, rightsize, tidal, health in parallel
  const [zombieResp, rightsizeResp, tidalResp, healthResp] = await Promise.allSettled([
    apiClient.get(`/api/analysis/tasks/${taskId}/zombie`).catch(() => null),
    apiClient.get(`/api/analysis/tasks/${taskId}/rightsize`).catch(() => null),
    apiClient.get(`/api/analysis/tasks/${taskId}/tidal`).catch(() => null),
    apiClient.get(`/api/analysis/tasks/${taskId}/health`).catch(() => null),
  ]);

  const result: Record<string, unknown> = {};

  if (zombieResp.status === 'fulfilled' && zombieResp.value?.data?.data) {
    result.zombieVM = zombieResp.value.data.data;
  }
  if (rightsizeResp.status === 'fulfilled' && rightsizeResp.value?.data?.data) {
    result.rightSize = rightsizeResp.value.data.data;
  }
  if (tidalResp.status === 'fulfilled' && tidalResp.value?.data?.data) {
    result.tidal = tidalResp.value.data.data;
  }
  if (healthResp.status === 'fulfilled' && healthResp.value?.data?.data) {
    result.healthScore = healthResp.value.data.data;
  }

  return result;
}

/**
 * Run an analysis job
 * Note: Backend runs analysis synchronously and returns results directly
 * This function returns the analysis results, not a job ID
 */
export async function runAnalysisJob(
    taskId: number,
    analysisType: "zombie" | "rightsize" | "tidal",
    config?: Record<string, unknown>
): Promise<unknown[]> {
    const response = await apiClient.post(`/api/analysis/tasks/${taskId}/${analysisType}`, config || {});
    return response.data.data as unknown[];
}

// Note: getAnalysisJobStatus removed - backend uses synchronous analysis
