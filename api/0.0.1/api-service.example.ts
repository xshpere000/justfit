/**
 * JustFit Backend API 服务示例
 * Version: 0.0.1
 *
 * 此文件展示如何在 Vue 3 前端项目中调用后端 API
 * 实际使用时，Wails 会自动生成绑定代码
 */

import { ref, reactive } from 'vue';
import type {
  ConnectionRequest,
  Connection,
  TestConnectionRequest,
  TestConnectionResult,
  TaskInfo,
  ClusterListItem,
  HostListItem,
  VMListItem,
  ZombieVMConfig,
  ZombieVMResult,
  RightSizeConfig,
  RightSizeResult,
  HealthScoreResult,
  DashboardStats,
  SystemSettings,
  AlertListItem,
  AlertStats,
  AnalysisRequest,
  AnalysisResponse,
} from './types';

// ==================== 连接管理服务 ====================

export const useConnectionService = () => {
  const connections = ref<Connection[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 创建连接
   */
  const createConnection = async (req: ConnectionRequest): Promise<number> => {
    loading.value = true;
    error.value = null;
    try {
      // Wails 会自动生成以下方法调用
      const id = await window.go.main.App.CreateConnection(req);
      await listConnections(); // 刷新列表
      return id;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 测试连接
   */
  const testConnection = async (req: TestConnectionRequest): Promise<TestConnectionResult> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.TestConnection(req.id, req.host, req.username, req.password, req.platform, req.insecure);
      return result as TestConnectionResult;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取连接列表
   */
  const listConnections = async (): Promise<Connection[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListConnections();
      // 解析 JSON 字符串
      const data = JSON.parse(result as string);
      connections.value = data as Connection[];
      return connections.value;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取连接详情
   */
  const getConnection = async (id: number): Promise<Connection> => {
    try {
      const result = await window.go.main.App.GetConnection(id);
      return result as Connection;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  /**
   * 更新连接
   */
  const updateConnection = async (req: ConnectionRequest & { id: number }): Promise<void> => {
    loading.value = true;
    error.value = null;
    try {
      await window.go.main.App.UpdateConnection({
        id: req.id,
        name: req.name,
        platform: req.platform,
        host: req.host,
        port: req.port,
        username: req.username,
        password: req.password,
        insecure: req.insecure,
      });
      await listConnections();
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 删除连接
   */
  const deleteConnection = async (id: number): Promise<void> => {
    loading.value = true;
    error.value = null;
    try {
      await window.go.main.App.DeleteConnection(id);
      await listConnections();
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  return {
    connections,
    loading,
    error,
    createConnection,
    testConnection,
    listConnections,
    getConnection,
    updateConnection,
    deleteConnection,
  };
};

// ==================== 采集任务服务 ====================

export const useTaskService = () => {
  const tasks = ref<TaskInfo[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 创建采集任务
   */
  const createCollectTask = async (connectionId: number, dataTypes: string[], metricsDays: number): Promise<number> => {
    loading.value = true;
    error.value = null;
    try {
      const taskId = await window.go.main.App.CreateCollectTask({
        connection_id: connectionId,
        data_types: dataTypes,
        metrics_days: metricsDays,
      });
      // 启动轮询获取任务状态
      startPolling();
      return taskId;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取任务列表
   */
  const listTasks = async (status?: string): Promise<TaskInfo[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListTasks(status || '', 100, 0);
      tasks.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 停止任务
   */
  const stopTask = async (id: number): Promise<void> => {
    try {
      await window.go.main.App.StopTask(id);
      await listTasks();
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  /**
   * 重试任务
   */
  const retryTask = async (id: number): Promise<number> => {
    try {
      const newTaskId = await window.go.main.App.RetryTask(id);
      await listTasks();
      return newTaskId;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  /**
   * 获取任务日志
   */
  const getTaskLogs = async (id: number): Promise<string[]> => {
    try {
      const logs = await window.go.main.App.GetTaskLogs(id, 100);
      return logs.map((log: any) => `${log.Timestamp} [${log.Level}] ${log.Message}`);
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  // 轮询任务状态
  const startPolling = () => {
    const interval = setInterval(async () => {
      await listTasks();
      // 如果所有任务都完成，停止轮询
      const hasRunning = tasks.value.some(t => t.Status === 'running');
      if (!hasRunning) {
        clearInterval(interval);
      }
    }, 2000);
  };

  return {
    tasks,
    loading,
    error,
    createCollectTask,
    listTasks,
    stopTask,
    retryTask,
    getTaskLogs,
  };
};

// ==================== 资源查询服务 ====================

export const useResourceService = () => {
  const clusters = ref<ClusterListItem[]>([]);
  const hosts = ref<HostListItem[]>([]);
  const vms = ref<VMListItem[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 获取集群列表
   */
  const listClusters = async (connectionId: number): Promise<ClusterListItem[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListClusters(connectionId);
      clusters.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取主机列表
   */
  const listHosts = async (connectionId: number): Promise<HostListItem[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListHosts(connectionId);
      hosts.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取虚拟机列表
   */
  const listVMs = async (connectionId: number): Promise<VMListItem[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListVMs(connectionId);
      vms.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 获取指标数据
   */
  const getMetrics = async (vmId: number, metricType: string, days: number) => {
    try {
      const result = await window.go.main.App.GetMetrics(vmId, metricType, days);
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  return {
    clusters,
    hosts,
    vms,
    loading,
    error,
    listClusters,
    listHosts,
    listVMs,
    getMetrics,
  };
};

// ==================== 分析服务 ====================

export const useAnalysisService = () => {
  const zombieVMs = ref<ZombieVMResult[]>([]);
  const rightSizeResults = ref<RightSizeResult[]>([]);
  const healthScore = ref<HealthScoreResult | null>(null);
  const loading = ref(false);
  const analyzing = ref(false);
  const error = ref<string | null>(null);

  /**
   * 僵尸 VM 检测
   */
  const detectZombieVMs = async (connectionId: number, config?: ZombieVMConfig): Promise<ZombieVMResult[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.DetectZombieVMs(
        connectionId,
        config || {
          analysis_days: 7,
          cpu_threshold: 5,
          memory_threshold: 10,
          min_confidence: 0.7,
        }
      );
      zombieVMs.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Right Size 分析
   */
  const analyzeRightSize = async (connectionId: number, config?: RightSizeConfig): Promise<RightSizeResult[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.AnalyzeRightSize(
        connectionId,
        config || {
          analysis_days: 7,
          buffer_ratio: 1.2,
        }
      );
      rightSizeResults.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 健康度分析
   */
  const analyzeHealthScore = async (connectionId: number): Promise<HealthScoreResult> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.AnalyzeHealthScore(connectionId, {});
      healthScore.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 运行统一分析
   */
  const runAnalysis = async (req: AnalysisRequest): Promise<AnalysisResponse> => {
    analyzing.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.RunAnalysis(req);
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      analyzing.value = false;
    }
  };

  /**
   * 获取分析汇总
   */
  const getAnalysisSummary = async (connectionId: number) => {
    try {
      const result = await window.go.main.App.GetAnalysisSummary(connectionId);
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  return {
    zombieVMs,
    rightSizeResults,
    healthScore,
    loading,
    analyzing,
    error,
    detectZombieVMs,
    analyzeRightSize,
    analyzeHealthScore,
    runAnalysis,
    getAnalysisSummary,
  };
};

// ==================== 仪表盘服务 ====================

export const useDashboardService = () => {
  const stats = ref<DashboardStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 获取仪表盘统计数据
   */
  const getStats = async (): Promise<DashboardStats> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.GetDashboardStats();
      stats.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  return {
    stats,
    loading,
    error,
    getStats,
  };
};

// ==================== 系统配置服务 ====================

export const useSettingsService = () => {
  const settings = ref<SystemSettings | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 获取系统配置
   */
  const getSettings = async (): Promise<SystemSettings> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.GetSettings();
      settings.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 更新系统配置
   */
  const updateSettings = async (newSettings: SystemSettings): Promise<void> => {
    loading.value = true;
    error.value = null;
    try {
      await window.go.main.App.UpdateSettings(newSettings);
      settings.value = newSettings;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  return {
    settings,
    loading,
    error,
    getSettings,
    updateSettings,
  };
};

// ==================== 告警服务 ====================

export const useAlertService = () => {
  const alerts = ref<AlertListItem[]>([]);
  const stats = ref<AlertStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 获取告警列表
   */
  const listAlerts = async (acknowledged?: boolean): Promise<AlertListItem[]> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.go.main.App.ListAlerts(
        acknowledged === undefined ? null : acknowledged,
        100,
        0
      );
      alerts.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  /**
   * 标记告警
   */
  const markAlert = async (id: number, acknowledged: boolean): Promise<void> => {
    try {
      await window.go.main.App.MarkAlert({ id, acknowledged });
      await listAlerts();
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  /**
   * 获取告警统计
   */
  const getAlertStats = async (): Promise<AlertStats> => {
    try {
      const result = await window.go.main.App.GetAlertStats();
      stats.value = result;
      return result;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    }
  };

  return {
    alerts,
    stats,
    loading,
    error,
    listAlerts,
    markAlert,
    getAlertStats,
  };
};
