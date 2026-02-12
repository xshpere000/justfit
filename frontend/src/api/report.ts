import type { ReportData } from './types'
import { utils, write } from 'xlsx'

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

// 导出任务报告
export async function exportTaskReport(taskId: string): Promise<string> {
    // 获取任务详情数据，然后导出
    // 暂时 unimplemented
    console.log('Export task report:', taskId)
    return ''
}
