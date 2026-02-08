import type {
  ConnectionInfo,
  CreateConnectionRequest,
  CollectionConfig,
  CollectionResult
} from './types'

// 导入 Wails 生成的 API
// 这些会在运行时通过 wails dev 生成
let App: any = null

// 动态导入 Wails 生成的模块
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

// ========== 连接管理 ==========

// 超时封装
function withTimeout<T>(promise: Promise<T>, timeoutMs: number, operation: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`${operation} 请求超时 (${timeoutMs}ms)`)), timeoutMs)
    )
  ])
}

export async function listConnections(): Promise<ConnectionInfo[]> {
  const app = await loadWailsApp()
  return withTimeout(app.ListConnections(), 5000, 'ListConnections')
}

export async function createConnection(
  req: CreateConnectionRequest
): Promise<number> {
  const app = await loadWailsApp()
  return withTimeout(app.CreateConnection(req), 30000, 'CreateConnection')
}

export async function testConnection(id: number): Promise<string> {
  const app = await loadWailsApp()
  return withTimeout(app.TestConnection(id), 60000, 'TestConnection')
}

export async function deleteConnection(id: number): Promise<void> {
  const app = await loadWailsApp()
  return await app.DeleteConnection(id)
}

// ========== 数据采集 ==========

export async function collectData(
  config: CollectionConfig
): Promise<CollectionResult> {
  const app = await loadWailsApp()
  return await app.CollectData(config)
}

// ========== 数据查询 ==========

export async function getVMList(connectionId: number): Promise<string> {
  const app = await loadWailsApp()
  return withTimeout(app.GetVMList(connectionId), 120000, 'GetVMList')
}

export async function getHostList(connectionId: number): Promise<string> {
  const app = await loadWailsApp()
  return withTimeout(app.GetHostList(connectionId), 60000, 'GetHostList')
}

export async function getClusterList(connectionId: number): Promise<string> {
  const app = await loadWailsApp()
  return withTimeout(app.GetClusterList(connectionId), 30000, 'GetClusterList')
}

export const ConnectionApi = {
  list: listConnections,
  create: createConnection,
  test: createConnection, // Wizard uses test() to create and return ID
  testConnectivity: testConnection, // Real test connection
  delete: deleteConnection,
  collectData: async (configOrId: number | CollectionConfig) => {
    if (typeof configOrId === 'number') {
      return collectData({
        connection_id: configOrId,
        data_types: ['clusters', 'hosts', 'vms'], // Default to basic info
        metrics_days: 0
      })
    }
    return collectData(configOrId)
  },
  getVMList: getVMList,
  getHostList: getHostList,
  getClusterList: getClusterList
}
