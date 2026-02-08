import type {
  ZombieVMConfig,
  ZombieVMResult,
  RightSizeConfig,
  RightSizeResult,
  TidalConfig,
  TidalResult,
  HealthScoreResult
} from './types'

// 动态导入 Wails 生成的模块
let App: any = null

async function loadWailsApp() {
  if (!App) {
    try {
      const module = await import('../../wailsjs/go/main/App')
      App = module
    } catch (error) {
      console.error('Failed to load Wails App:', error)
    }
  }
  return App
}

// ========== 僵尸 VM 检测 ==========

export async function detectZombieVMs(
  connectionId: number,
  config: ZombieVMConfig = {}
): Promise<ZombieVMResult[]> {
  const app = await loadWailsApp()
  return await app.DetectZombieVMs(connectionId, config)
}

// ========== Right Size 分析 ==========

export async function analyzeRightSize(
  connectionId: number,
  config: RightSizeConfig = {}
): Promise<RightSizeResult[]> {
  const app = await loadWailsApp()
  return await app.AnalyzeRightSize(connectionId, config)
}

// ========== 潮汐检测 ==========

export async function detectTidalPattern(
  connectionId: number,
  config: TidalConfig = {}
): Promise<TidalResult[]> {
  const app = await loadWailsApp()
  return await app.DetectTidalPattern(connectionId, config)
}

// ========== 健康度分析 ==========

export async function analyzeHealthScore(
  connectionId: number
): Promise<HealthScoreResult> {
  const app = await loadWailsApp()
  return await app.AnalyzeHealthScore(connectionId)
}
