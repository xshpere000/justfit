/**
 * JustFit Backend API 类型定义
 * 仅保留实际被引用的类型，分析相关类型在 api/analysis.ts 中定义
 */

export interface TaskInfo {
  id: number;
  type: string;
  name: string;
  status: string;
  progress: number;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  connectionId?: number;
  connectionName?: string;
  connectionHost?: string;
  host?: string;
  platform?: string;
  selectedVMs?: string[];
  selectedVMCount?: number;
  collectedVMCount?: number;
  currentStep?: string;
  analysisResults?: Record<string, boolean>;
}

export interface VersionCheckResult {
  needsRebuild: boolean;
  currentVersion: string;
  databaseSize: number;
  hasData: boolean;
  latestVersion: string;
  message: string;
}
