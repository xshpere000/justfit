/**
 * Axios HTTP Client Configuration
 * Base client for all API requests
 */

import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";

/**
 * 动态获取后端 API 地址
 *
 * 规则：
 * 1. 如果是 localhost/127.0.0.1，使用 localhost:22631
 * 2. 如果是局域网 IP，使用当前主机名:22631
 * 3. 生产环境可使用环境变量覆盖
 */
function getApiBaseUrl(): string {
    // 检查环境变量
    if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL;
    }

    // 动态检测
    if (typeof window !== "undefined") {
        const hostname = window.location.hostname;
        const protocol = window.location.protocol; // http: 或 https:

        // 开发环境：使用当前页面的主机名
        // 例如：访问 http://192.168.1.100:22632，后端就是 http://192.168.1.100:22631
        return `${protocol}//${hostname}:22631`;
    }

    // 默认回退
    return "http://localhost:22631";
}

// API base URL (动态获取)
const API_BASE_URL = getApiBaseUrl();

// 调试：输出 API 地址
console.log("[API Client] Backend URL:", API_BASE_URL);

// Create axios instance
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// Request interceptor - 添加调试信息
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // Add timestamp to prevent caching
        if (config.params) {
            config.params = { ...config.params, _t: Date.now() };
        } else {
            config.params = { _t: Date.now() };
        }

        // 调试：输出请求信息
        console.log("[API Request]", config.method?.toUpperCase(), config.baseURL + config.url);

        return config;
    },
    (error: AxiosError) => {
        return Promise.reject(error);
    }
);

// Response interceptor
apiClient.interceptors.response.use(
    (response: AxiosResponse) => {
        return response;
    },
    (error: AxiosError<{ error: { code: string; message: string } }>) => {
        // 详细的错误日志
        console.error("[API Error]", {
            message: error.message,
            code: error.code,
            status: error.response?.status,
            url: error.config?.url,
            baseURL: error.config?.baseURL,
        });

        // Handle common errors
        if (error.response) {
            const status = error.response.status;
            const data = error.response.data;

            switch (status) {
                case 401:
                    console.error("Unauthorized");
                    break;
                case 403:
                    console.error("Forbidden");
                    break;
                case 404:
                    console.error("Resource not found");
                    break;
                case 500:
                    console.error("Internal server error");
                    break;
                default:
                    console.error(`API Error: ${data?.error?.message || error.message}`);
            }
        } else if (error.request) {
            console.error(`Network error - 无法连接到后端 (${error.config?.baseURL})`);
            console.error("请检查：");
            console.error("  1. 后端服务是否已启动");
            console.error("  2. 防火墙是否允许访问端口 22631");
            console.error("  3. 后端和前端是否在同一台服务器上");
        } else {
            console.error(`Request error: ${error.message}`);
        }

        return Promise.reject(error);
    }
);

// Get backend URL from Electron if available
export async function getBackendUrl(): Promise<string> {
    if (typeof window !== "undefined" && window.electronAPI) {
        return await window.electronAPI.getBackendUrl();
    }
    return API_BASE_URL;
}

// Check backend health
export async function checkBackendHealth(): Promise<boolean> {
    try {
        const response = await apiClient.get("/api/system/health");
        return response.data.status === "healthy";
    } catch {
        return false;
    }
}
