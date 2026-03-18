/**
 * Analysis API
 * Analysis engine endpoints
 */

import { apiClient } from "./client";

// ============ 分析结果类型定义 ============
// 直接使用后端返回的字段名，不做任何映射

/**
 * 闲置检测分析结果
 * API: GET /api/analysis/tasks/{task_id}/idle
 */
export interface IdleResult {
    vmName: string;
    cluster: string;
    hostIp: string;
    isIdle: boolean;
    idleType: string;
    confidence: number;
    riskLevel: string;
    daysInactive: number;
    lastActivityTime: string | null;
    recommendation: string;
}

/**
 * 资源分析完整响应
 * API: GET /api/analysis/tasks/{task_id}/resource
 */
export interface ResourceAnalysisResponse {
    resourceOptimization: any[];
    tidal: any[];
    summary: Record<string, unknown>;
}

/**
 * 健康评分分析结果
 * API: GET /api/analysis/tasks/{task_id}/health
 */
export interface HealthScoreResult {
    overallScore: number;
    grade: string;
    subScores: {
        overcommit: number;
        balance: number;
        hotspot: number;
    };
    clusterCount: number;
    hostCount: number;
    vmCount: number;
    overcommitResults: Array<{
        clusterName: string;
        cpuOvercommit: number;
        memoryOvercommit: number;
        cpuRisk: string;
        memoryRisk: string;
    }>;
    balanceResults: Array<{
        clusterName: string;
        coefficientOfVariation: number;
        balanceLevel: string;
    }>;
    hotspotHosts: Array<{
        hostName: string;
        clusterName: string;
        vmDensity: number;
        vmCount: number;
        cpuCores: number;
        riskLevel: string;
    }>;
    overcommitScore: number;
    balanceScore: number;
    hotspotScore: number;
    findings: Array<{
        severity: string;
        category: string;
        cluster?: string;
        host?: string;
        description: string;
        details: Record<string, unknown>;
    }>;
    recommendations: string[];
}

// ============ 评估模式配置类型定义 ============

/**
 * 闲置检测配置
 */
export interface IdleConfig {
    days: number;
    cpuThreshold: number;
    memoryThreshold: number;
    minConfidence: number;
}

/**
 * 资源配置优化配置
 */
export interface RightSizeConfig {
    days: number;
    cpuBufferPercent: number;
    memoryBufferPercent: number;
    minConfidence: number;
}

/**
 * 使用模式分析配置
 */
export interface UsagePatternConfig {
    cvThreshold: number;
    peakValleyRatio: number;
}

/**
 * 资源分析配置
 */
export interface ResourceConfig {
    rightsize: RightSizeConfig;
    usagePattern: UsagePatternConfig;
}

/**
 * 健康评分配置
 */
export interface HealthConfig {
    overcommitThreshold: number;
    hotspotThreshold: number;
    balanceThreshold: number;
}

/**
 * 完整评估模式配置
 */
export interface AnalysisModeConfig {
    idle: IdleConfig;
    resource: ResourceConfig;
    health: HealthConfig;
}

/**
 * 评估模式类型
 */
export type AnalysisModeType = 'safe' | 'saving' | 'aggressive' | 'custom';

/**
 * 评估模式响应
 */
export interface AnalysisModeResponse {
    mode: AnalysisModeType;
    modeName: string;
    description: string;
    config: AnalysisModeConfig;
    availableModes: Array<{
        mode: AnalysisModeType;
        name: string;
        description: string;
    }>;
}

// ============ 分析 API 函数 ============

/**
 * 获取闲置检测分析结果
 * API: GET /api/analysis/tasks/{task_id}/idle
 */
export async function getIdleResults(taskId: number): Promise<IdleResult[]> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/idle`);
    return response.data.data as IdleResult[];
}

/**
 * 运行闲置检测分析
 * API: POST /api/analysis/tasks/{task_id}/idle
 */
export async function runIdleAnalysis(taskId: number, config?: Record<string, unknown>): Promise<IdleResult[]> {
    // 如果 config 未定义，发送空对象，让后端从任务配置中读取自定义配置
    const body = config ?? {};
    const response = await apiClient.post(`/api/analysis/tasks/${taskId}/idle`, body);
    return response.data.data as IdleResult[];
}

/**
 * 获取资源分析结果
 * API: GET /api/analysis/tasks/{task_id}/resource
 */
export async function getResourceResults(taskId: number): Promise<ResourceAnalysisResponse> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/resource`);
    return response.data.data as ResourceAnalysisResponse;
}

/**
 * 运行资源分析
 * API: POST /api/analysis/tasks/{task_id}/resource
 */
export async function runResourceAnalysis(taskId: number, config?: Record<string, unknown>): Promise<ResourceAnalysisResponse> {
    // 如果 config 未定义，发送空对象，让后端从任务配置中读取自定义配置
    const body = config ?? {};
    const response = await apiClient.post(`/api/analysis/tasks/${taskId}/resource`, body);
    return response.data.data as ResourceAnalysisResponse;
}

/**
 * 获取健康评分分析结果
 * API: GET /api/analysis/tasks/{task_id}/health
 */
export async function getHealthResults(taskId: number): Promise<HealthScoreResult> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/health`);
    return response.data.data as HealthScoreResult;
}

/**
 * 运行健康评分分析
 * API: POST /api/analysis/tasks/{task_id}/health
 */
export async function runHealthAnalysis(taskId: number, config?: Record<string, unknown>): Promise<HealthScoreResult> {
    // 如果 config 未定义，发送空对象，让后端从任务配置中读取自定义配置
    const body = config ?? {};
    const response = await apiClient.post(`/api/analysis/tasks/${taskId}/health`, body);
    return response.data.data as HealthScoreResult;
}

// ============ 评估模式相关 API (供 AnalysisModeTab 使用) ============

/**
 * 获取所有评估模式
 * API: GET /api/analysis/modes
 */
export async function getAnalysisModes(): Promise<Record<string, unknown>> {
    const response = await apiClient.get("/api/analysis/modes");
    return response.data.data as Record<string, unknown>;
}

/**
 * 获取特定评估模式配置
 * API: GET /api/analysis/modes/{mode}
 */
export async function getAnalysisMode(mode: string): Promise<AnalysisModeConfig> {
    const response = await apiClient.get(`/api/analysis/modes/${mode}`);
    return response.data.data as AnalysisModeConfig;
}

/**
 * 更新任务的自定义评估配置
 * API: PUT /api/tasks/{task_id}/custom-config
 *
 * 将自定义配置保存到任务的 config.customConfig 字段中，
 * 重新评估时会使用此配置。
 */
export async function updateTaskCustomConfig(taskId: number, analysisType: string, config: Record<string, unknown>): Promise<void> {
    await apiClient.put(`/api/tasks/${taskId}/custom-config`, { analysisType, config });
}

/**
 * 更新任务的分析模式（非 custom 模式时使用）
 * API: PUT /api/tasks/{task_id}/mode
 */
export async function updateTaskMode(taskId: number, mode: string): Promise<void> {
    await apiClient.put(`/api/tasks/${taskId}/mode`, { mode });
}

/**
 * 获取分析汇总（可释放主机等）
 * API: GET /api/analysis/tasks/{task_id}/summary?optimizations=resource,idle
 */
export async function getAnalysisSummary(taskId: number, optimizations: string): Promise<any> {
    const response = await apiClient.get(`/api/analysis/tasks/${taskId}/summary`, {
        params: { optimizations }
    });
    return response.data.data;
}
