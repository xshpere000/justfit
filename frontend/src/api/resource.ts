/**
 * Resource API
 * Resource query endpoints (clusters, hosts, VMs)
 */

import { apiClient } from "./client";

// Types
export interface Cluster {
    id: number;
    connectionId: number;
    name: string;
    datacenter: string;
    totalCpu: number;
    totalMemory: number;
    numHosts: number;
    numVms: number;
    clusterKey: string;
    collectedAt: string;
}

export interface Host {
    id: number;
    connectionId: number;
    name: string;
    datacenter: string;
    ipAddress: string;
    cpuCores: number;
    cpuMhz: number;
    memoryBytes: number;
    numVms: number;
    powerState: string;
    overallStatus: string;
    collectedAt: string;
}

export interface VM {
    id: number;
    connectionId: number;
    name: string;
    datacenter: string;
    uuid: string;
    vmKey: string;
    cpuCount: number;
    memoryBytes: number;
    powerState: string;
    guestOs: string;
    ipAddress: string;
    hostName: string;
    hostIp: string;
    connectionState: string;
    overallStatus: string;
    collectedAt: string;
}

export interface VMListResponse {
    items: VM[];
    total: number;
}

/**
 * Get clusters for a connection
 */
export async function getClusters(connectionId: number): Promise<Cluster[]> {
    const response = await apiClient.get(`/api/resources/connections/${connectionId}/clusters`);
    // 后端返回 { success: true, data: { items: [...], total: ... } }
    return response.data.data.items || [];
}

/**
 * Get hosts for a connection
 */
export async function getHosts(connectionId: number): Promise<Host[]> {
    const response = await apiClient.get(`/api/resources/connections/${connectionId}/hosts`);
    // 后端返回 { success: true, data: { items: [...], total: ... } }
    return response.data.data.items || [];
}

/**
 * Get VMs for a connection
 *
 * Note: 后端有两个相关路由：
 * - /api/resources/connections/{id}/vms - 返回已采集的VM数据（支持分页和过滤）
 * - /api/resources/connections/{id}/vms/list - 返回可采集的VM列表（实时获取）
 *
 * 当前使用的是 /vms 路由，适用于查看已采集的数据
 */
export async function getVMs(
    connectionId: number,
    params?: {
        page?: number;
        size?: number;
        search?: string;
        powerState?: string;
    }
): Promise<VMListResponse> {
    const response = await apiClient.get(`/api/resources/connections/${connectionId}/vms`, { params });
    return response.data.data;
}

/**
 * Start collection for a connection
 * Note: 后端路由是 /api/resources/connections/{id}/collect
 */
export async function startCollection(
    connectionId: number,
    options?: {
        selectedVMs?: string[];
        collectMetrics?: boolean;
        metricsDays?: number;
    }
): Promise<{ taskId: number }> {
    const response = await apiClient.post(`/api/resources/connections/${connectionId}/collect`, options);
    return response.data.data;
}
