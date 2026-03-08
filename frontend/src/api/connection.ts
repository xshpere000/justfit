/**
 * Connection API
 * Connection management endpoints
 */

import { apiClient } from "./client";
import { getClusters, getHosts, getVMs } from "./resource";

// Types
export interface Connection {
    id: number;
    name: string;
    platform: "vcenter" | "h3c-uis";
    host: string;
    port: number;
    username: string;
    insecure: boolean;
    status: string;
    lastSync: string | null;
    createdAt: string;
    updatedAt: string;
}

export interface ConnectionCreate {
    name: string;
    platform: "vcenter" | "h3c-uis";
    host: string;
    port?: number;
    username: string;
    password: string;
    insecure?: boolean;
}

export interface ConnectionUpdate {
    name?: string;
    host?: string;
    port?: number;
    username?: string;
    password?: string;
    insecure?: boolean;
}

export interface ConnectionListResponse {
    items: Connection[];
    total: number;
}

export interface ConnectionTestResult {
    status: string;
    message: string;
}

// Collection types (compatibility)
export interface CollectionConfig {
    connectionId: number;
    dataTypes: string[];
    metricsDays: number;
}

export interface CollectionResult {
    success: boolean;
    message: string;
    clusters?: number;
    hosts?: number;
    vms?: number;
}

export interface ClusterListItem {
    id: number;
    name: string;
    datacenter: string;
    totalCpu: number;
    totalMemoryGb: number;
    numHosts: number;
    numVms: number;
    status: string;
}

export interface HostListItem {
    id: number;
    name: string;
    datacenter: string;
    ipAddress: string;
    cpuCores: number;
    memoryGb: number;
    numVms: number;
    powerState: string;
}

export interface VMListItem {
    id: number;
    name: string;
    datacenter: string;
    hostIp: string;
    cpuCount: number;
    memoryGb: number;
    ipAddress: string;
    powerState: string;
}

// Version types (compatibility)
export interface VersionCheckResult {
    currentVersion: string;
    latestVersion: string;
    needsRebuild: boolean;
    databaseSize: number;
    hasData: boolean;
}

export interface AppVersionInfo {
    version: string;
    isDevelopment: boolean;
}

/**
 * List all connections
 */
export async function listConnections(params?: {
    page?: number;
    size?: number;
}): Promise<ConnectionListResponse> {
    const response = await apiClient.get("/api/connections", { params });
    return response.data.data;
}

/**
 * Get connection by ID
 */
export async function getConnection(id: number): Promise<Connection> {
    const response = await apiClient.get(`/api/connections/${id}`);
    return response.data.data;
}

/**
 * Create new connection
 */
export async function createConnection(data: ConnectionCreate): Promise<Connection> {
    const response = await apiClient.post("/api/connections", data);
    return response.data.data;
}

/**
 * Update connection
 */
export async function updateConnection(
    id: number,
    data: ConnectionUpdate
): Promise<Connection> {
    const response = await apiClient.put(`/api/connections/${id}`, data);
    return response.data.data;
}

/**
 * Delete connection
 */
export async function deleteConnection(id: number): Promise<void> {
    await apiClient.delete(`/api/connections/${id}`);
}

/**
 * Test connection
 */
export async function testConnection(id: number): Promise<ConnectionTestResult> {
    const response = await apiClient.post(`/api/connections/${id}/test`);
    return response.data.data;
}

/**
 * Test connection and fetch VM list (without full collection)
 * Used in Wizard to quickly get VM list
 */
export async function testConnectionAndFetchVMs(id: number): Promise<{
    status: string;
    message: string;
    vms: any[];
    total: number;
}> {
    const response = await apiClient.post(`/api/connections/${id}/test-and-fetch-vms`);
    return response.data.data;
}

// Compatibility functions for old code
export const ConnectionApi = {
    create: async (data: ConnectionCreate) => createConnection(data),
    update: async (id: number, data: ConnectionUpdate) => updateConnection(id, data),
    delete: async (id: number) => deleteConnection(id),
    test: async (id: number) => testConnection(id),
};

export const CollectionApi = {
    collect: async (connectionId: number, options?: any) => {
        const response = await apiClient.post(`/api/resources/connections/${connectionId}/collect`, options || {});
        return response.data.data;
    },
};

export const ResourceApi = {
    getVMList: async (connectionId: number) => {
        const response = await apiClient.get(`/api/resources/connections/${connectionId}/vms`);
        // 后端返回 { success: true, data: { items: [...], total: ... } }
        return response.data.data;
    },
    getClusterList: async (connectionId: number) => {
        return getClusters(connectionId);
    },
    getHostList: async (connectionId: number) => {
        return getHosts(connectionId);
    },
};

export async function collectData(config: CollectionConfig): Promise<CollectionResult> {
    const response = await apiClient.post(`/api/resources/connections/${config.connectionId}/collect`, {
        collectMetrics: config.dataTypes.includes('metrics'),
        days: config.metricsDays,
    });
    return response.data.data;
}

export async function getClusterListRaw(connectionId: number): Promise<ClusterListItem[]> {
    const clusters = await getClusters(connectionId);
    return clusters.map(c => ({
        id: c.id,
        name: c.name,
        datacenter: c.datacenter,
        totalCpu: c.totalCpu,
        totalMemoryGb: Math.round(c.totalMemory / (1024 ** 3)),
        numHosts: c.numHosts,
        numVms: c.numVms,
        status: 'collected',
    }));
}

export async function getHostListRaw(connectionId: number): Promise<HostListItem[]> {
    const hosts = await getHosts(connectionId);
    return hosts.map(h => ({
        id: h.id,
        name: h.name,
        datacenter: h.datacenter,
        ipAddress: h.ipAddress,
        cpuCores: h.cpuCores,
        memoryGb: Math.round(h.memoryBytes / (1024 ** 3)),
        numVms: h.numVms,
        powerState: h.powerState,
    }));
}

export async function getVMList(connectionId: number): Promise<VMListItem[]> {
    const response = await apiClient.get(`/api/resources/connections/${connectionId}/vms`);
    const vms = response.data.data.items || [];
    return vms.map((v: any) => ({
        id: v.id,
        name: v.name,
        datacenter: v.datacenter || '',
        hostIp: v.hostIp || '',
        cpuCount: v.cpuCount,
        memoryGb: v.memoryGb,
        ipAddress: v.ipAddress || '',
        powerState: v.powerState,
    }));
}

// Version API (compatibility)
export const VersionApi = {
    checkVersion: async (): Promise<VersionCheckResult> => {
        // Always return no rebuild needed for v0.0.3
        return {
            currentVersion: '0.0.3',
            latestVersion: '0.0.3',
            needsRebuild: false,
            databaseSize: 0,
            hasData: false,
        };
    },
    getAppVersion: async (): Promise<AppVersionInfo> => {
        return {
            version: '0.0.3',
            isDevelopment: true,
        };
    },
    rebuildDatabase: async (): Promise<void> => {
        // No-op in new architecture
    },
};
