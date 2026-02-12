import type { ReportData } from './types'
import { utils, write } from 'xlsx'
import * as App from '../../wailsjs/go/main/App'

export type ReportFormat = 'json' | 'html' | 'xlsx'

export interface ReportExportOptions {
  format: ReportFormat
  outputDir?: string
}

// 导出报告
// 前端直接生成文件下载，不再依赖后端接口
export async function exportReport(
  data: any[],
  options: ReportExportOptions = { format: 'xlsx' }
): Promise<string> {
  const filename = 'justfit_report_' + Date.now() + '.' + options.format

  if (options.format === 'json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    downloadBlob(blob, filename)
    return filename
  }

  // XLSX export
  const ws = utils.json_to_sheet(data)
  const wb = utils.book_new()
  utils.book_append_sheet(wb, ws, 'Report')

  const wbout = write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([wbout], { type: 'application/octet-stream' })
  downloadBlob(blob, filename)

  return filename
}

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

// 导出任务报告（后端生成）
export async function exportTaskReport(params: {
  taskId: string
  connectionId: number
  reportTypes: string[]
  title?: string
}): Promise<string> {
  const response = await App.GenerateReport({
    title: params.title || ('任务报告-' + params.taskId),
    connection_id: params.connectionId,
    report_types: params.reportTypes
  })

  if (!response.success) {
    throw new Error(response.message || '报告生成失败')
  }

  if (response.files && response.files.length > 0) {
    return response.files[0]
  }

  return response.message || '报告已生成'
}
