<template>
  <div class="task-detail-page">
    <!-- 任务头部 -->
    <div class="task-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" circle plain @click="goHome" />
      </div>
      <div class="header-center">
        <div class="task-title">
          <h1>{{ task?.name }}</h1>
          <el-tag :type="getStatusType(task?.status)" size="small">
            {{ getStatusText(task?.status) }}
          </el-tag>
        </div>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <el-button :icon="MoreFilled" circle />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="reEvaluate" v-if="task?.status === 'completed'">
                <el-icon>
                  <Refresh />
                </el-icon>
                重新评估
              </el-dropdown-item>
              <el-dropdown-item command="delete" v-if="task?.status !== 'running'">
                删除任务
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 任务运行中状态 -->
    <div v-if="task?.status === 'running' || task?.status === 'pending'" class="running-state">
      <el-card class="running-card">
        <div class="running-header">
          <el-icon :size="64" class="running-icon is-loading">
            <Loading />
          </el-icon>
          <h2 class="running-title">任务执行中</h2>
          <p class="running-step">{{ task.currentStep || '正在初始化...' }}</p>
        </div>

        <div class="running-progress">
          <el-progress :percentage="task.progress" :stroke-width="16" :show-text="true" striped striped-flow />
        </div>

        <div class="running-stats">
          <div class="stat-item">
            <span class="stat-label">采集状态</span>
            <span class="stat-value">正在采集虚拟机数据...</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">当前进度</span>
            <span class="stat-value">{{ task.progress }}%</span>
          </div>
        </div>

        <div class="running-actions">
          <el-button type="danger" plain :icon="CloseBold" @click="handleCancel">
            取消任务
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 任务已暂停状态 -->
    <div v-else-if="task?.status === 'paused'" class="paused-state">
      <el-card class="paused-card">
        <div class="paused-header">
          <el-icon :size="64" class="paused-icon">
            <VideoPause />
          </el-icon>
          <h2 class="paused-title">任务已暂停</h2>
          <p class="paused-step">{{ task.currentStep || '任务暂停中...' }}</p>
        </div>

        <div class="paused-progress">
          <el-progress :percentage="task.progress" :stroke-width="16" status="exception" />
        </div>

        <div class="paused-stats">
          <div class="stat-item">
            <span class="stat-label">采集状态</span>
            <span class="stat-value">正在采集虚拟机数据...</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">暂停时进度</span>
            <span class="stat-value">{{ task.progress }}%</span>
          </div>
        </div>

        <div class="paused-actions">
          <el-button type="danger" plain :icon="CloseBold" @click="handleCancel">
            取消任务
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 任务已完成状态 -->
    <div v-else-if="task?.status === 'completed'" class="completed-state">
      <!-- Tab 导航 -->
      <el-tabs v-model="activeTab" class="task-tabs">
        <el-tab-pane label="任务概览" name="overview">
          <div class="overview-grid">
            <!-- 完成横幅 -->
            <div class="completion-banner">
              <div class="cb-left">
                <el-icon :size="48" class="cb-icon">
                  <CircleCheck />
                </el-icon>
                <div class="cb-text">
                  <div class="cb-title">评估任务已完成</div>
                  <div class="cb-sub">
                    <span class="cb-platform">{{ task.platform === 'vcenter' ? 'vSphere' : 'UIS' }}</span>
                    <span class="cb-divider-inline">·</span>
                    <span class="cb-conn">{{ task.connectionHost || '未知平台' }}</span>
                  </div>
                </div>
              </div>
              <div class="cb-right">
                <div class="cb-stat">
                  <span class="cbs-value">{{ task.selectedVMCount }}</span>
                  <span class="cbs-label">台虚拟机</span>
                </div>
                <div class="cb-divider"></div>
                <div class="cb-stat">
                  <span class="cbs-value">{{ task.collectedVMCount || task.selectedVMCount }}</span>
                  <span class="cbs-label">已采集</span>
                </div>
                <div class="cb-divider"></div>
                <div class="cb-stat">
                  <span class="cbs-value">{{ completedAnalyses }}</span>
                  <span class="cbs-label">已完成分析</span>
                </div>
              </div>
            </div>

            <!-- 主体区 (严格限制网格比例) -->
            <div class="o-main">
              <!-- 左侧：分析 -->
              <div class="o-panel o-analysis">
                <div class="panel-hd">
                  <span class="ph-title"><el-icon>
                      <DataAnalysis />
                    </el-icon> 分析探索</span>
                </div>
                <div class="o-list">
                  <div v-for="analysis in analyses" :key="analysis.key" class="o-item"
                    :class="{ 'is-done': getAnalysisStatus(analysis.key), 'is-loading': isAnalysisLoading(analysis.key) }"
                    @click="!getAnalysisStatus(analysis.key) && !isAnalysisLoading(analysis.key) && runAnalysis(analysis.key)">

                    <div class="i-icon" :class="'i-' + analysis.color">
                      <el-icon v-if="isAnalysisLoading(analysis.key)" class="is-loading" :size="18">
                        <Loading />
                      </el-icon>
                      <el-icon v-else>
                        <component :is="analysis.icon" />
                      </el-icon>
                    </div>
                    <div class="i-core">
                      <div class="i-name">{{ analysis.title }}</div>
                      <div class="i-desc">{{ analysis.description }}</div>
                    </div>
                    <div class="i-act">
                      <el-tag v-if="getAnalysisStatus(analysis.key)" size="small" type="success" effect="light"
                        round>已完成</el-tag>
                      <el-button v-else-if="isAnalysisLoading(analysis.key)" type="primary" size="small" :loading="true"
                        round class="run-btn" disabled>
                        分析中
                      </el-button>
                      <el-button v-else type="primary" size="small" :icon="VideoPlay" plain round class="run-btn"
                        @click.stop="runAnalysis(analysis.key)">
                        运行
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 右侧：报告 -->
              <div class="o-panel o-report">
                <div class="panel-hd">
                  <span class="ph-title"><el-icon>
                      <DocumentCopy />
                    </el-icon> 分析报告</span>
                </div>

                <div class="o-actions">
                  <el-button class="exp-btn ex-excel" @click="exportReport('xlsx')" :loading="exporting.xlsx">
                    <el-icon>
                      <DocumentCopy />
                    </el-icon> <span>导出 Excel</span>
                  </el-button>
                  <el-button class="exp-btn ex-pdf" @click="exportReport('pdf')" :loading="exporting.pdf">
                    <el-icon>
                      <Notebook />
                    </el-icon> <span>生成 PDF</span>
                  </el-button>
                </div>

                <div class="o-history">
                  <div class="hist-label">最近生成</div>
                  <div v-if="reportHistory.length > 0" class="hist-list">
                    <div v-for="report in reportHistory" :key="report.id" class="h-item">
                      <div class="h-fmt" :class="report.format === 'excel' ? 'fmt-ex' : 'fmt-pd'">{{ report.format ===
                        'excel' ? 'Excel' : 'PDF' }}</div>
                      <div class="h-info">
                        <div class="h-name">{{ formatReportTime(report.createdAt) }}</div>
                        <div class="h-time">{{ formatFileSize(report.fileSize) }}</div>
                      </div>
                      <div class="h-actions">
                        <el-button circle size="small" type="primary" plain class="h-btn"
                          @click="downloadReport(report)" title="下载">
                          <el-icon>
                            <Download />
                          </el-icon>
                        </el-button>
                        <el-button circle size="small" type="danger" plain class="h-btn" @click="deleteReport(report)"
                          title="删除">
                          <el-icon>
                            <Delete />
                          </el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                  <div v-else class="hist-empty">
                    <span class="he-text">暂无历史报告</span>
                  </div>
                </div>
              </div>
            </div>



          </div>
        </el-tab-pane>

        <el-tab-pane label="分析结果" name="analysis">
          <div class="analysis-summary-content">
            <!-- 上方三栏布局 -->
            <div class="summary-top-panel">
              <!-- 左侧：当前集群资源情况 -->
              <div class="summary-panel summary-current">
                <div class="summary-panel-title">当前集群资源</div>
                <div class="summary-metrics">
                  <div class="summary-metric-item">
                    <div class="sm-value">{{ analysisSummaryData?.current?.totalHosts ?? '-' }}</div>
                    <div class="sm-label">物理主机</div>
                  </div>
                  <div class="summary-metric-item">
                    <div class="sm-value">{{ analysisSummaryData?.current?.totalCpuCores ?? '-' }}</div>
                    <div class="sm-label">CPU 核数</div>
                  </div>
                  <div class="summary-metric-item">
                    <div class="sm-value">{{ analysisSummaryData?.current?.totalMemoryGb != null ? analysisSummaryData.current.totalMemoryGb.toFixed(0) : '-' }}</div>
                    <div class="sm-label">内存 (GB)</div>
                  </div>
                  <div class="summary-metric-item">
                    <div class="sm-value">{{ analysisSummaryData?.current?.totalVms ?? '-' }}</div>
                    <div class="sm-label">虚拟机数</div>
                  </div>
                </div>
              </div>

              <!-- 中间：勾选优化项 -->
              <div class="summary-panel summary-controls">
                <div class="summary-panel-title">选择优化项</div>
                <div class="summary-checkboxes">
                  <el-checkbox
                    v-model="summaryOptimizations.resource"
                    :disabled="!hasAnalysisResults.resource"
                    @change="fetchAnalysisSummary"
                    class="summary-checkbox"
                  >
                    <span class="checkbox-label">资源优化</span>
                    <el-tag v-if="!hasAnalysisResults.resource" size="small" type="info" style="margin-left:6px">未运行</el-tag>
                  </el-checkbox>
                  <el-checkbox
                    v-model="summaryOptimizations.idle"
                    :disabled="!hasAnalysisResults.idle"
                    @change="fetchAnalysisSummary"
                    class="summary-checkbox"
                  >
                    <span class="checkbox-label">闲置检测</span>
                    <el-tag v-if="!hasAnalysisResults.idle" size="small" type="info" style="margin-left:6px">未运行</el-tag>
                  </el-checkbox>
                </div>
                <el-button
                  type="primary"
                  size="small"
                  :loading="analysisSummaryLoading"
                  @click="fetchAnalysisSummary"
                  class="summary-calc-btn"
                >
                  重新计算
                </el-button>
              </div>

              <!-- 右侧：优化后可节省资源 -->
              <div class="summary-panel summary-optimized">
                <div class="summary-panel-title">优化后可释放</div>
                <div v-if="analysisSummaryData" class="summary-metrics">
                  <div class="summary-metric-item highlight">
                    <div class="sm-value text-success">{{ analysisSummaryData.optimized?.freedCpuCores ?? '-' }}</div>
                    <div class="sm-label">释放 CPU 核</div>
                  </div>
                  <div class="summary-metric-item highlight">
                    <div class="sm-value text-success">{{ analysisSummaryData.optimized?.freedMemoryGb != null ? analysisSummaryData.optimized.freedMemoryGb.toFixed(0) : '-' }}</div>
                    <div class="sm-label">释放内存 (GB)</div>
                  </div>
                  <div class="summary-metric-item highlight">
                    <div class="sm-value text-primary">{{ analysisSummaryData.freeableHosts?.length ?? 0 }}</div>
                    <div class="sm-label">可释放主机</div>
                  </div>
                </div>
                <div v-else-if="analysisSummaryLoading" class="summary-loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>计算中...</span>
                </div>
                <div v-else class="summary-empty-hint">请勾选优化项后点击计算</div>
              </div>
            </div>

            <!-- 下方：可释放主机列表 -->
            <div class="summary-hosts-section" v-if="analysisSummaryData?.freeableHosts?.length > 0">
              <div class="summary-hosts-title">
                可释放的物理主机
                <el-tag size="small" type="success">{{ analysisSummaryData.freeableHosts.length }} 台</el-tag>
              </div>
              <el-table :data="analysisSummaryData.freeableHosts" stripe class="detail-table hosts-table">
                <el-table-column prop="hostName" label="主机名" min-width="160" show-overflow-tooltip />
                <el-table-column prop="hostIp" label="主机IP" width="140" />
                <el-table-column prop="cpuCores" label="CPU 核数" width="100" align="center" />
                <el-table-column prop="memoryGb" label="内存 (GB)" width="110" align="center">
                  <template #default="{ row }">{{ row.memoryGb?.toFixed(0) }}</template>
                </el-table-column>
                <el-table-column prop="currentVmCount" label="当前VM数" width="100" align="center" />
                <el-table-column label="原因" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="reason-text">{{ row.reason || '资源已被其他主机吸收' }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else-if="analysisSummaryData && analysisSummaryData.freeableHosts?.length === 0" class="summary-no-hosts">
              <el-empty description="根据当前选择的优化项，暂无可完全释放的物理主机" :image-size="80" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="资源优化" name="rightsize">
          <div class="analysis-content" v-if="hasAnalysisResults.resource">
            <!-- 汇总栏 -->
            <div class="rightsize-summary-bar" v-if="filteredResourceOptData.length > 0">
              <span class="rs-summary-text">
                共 <strong>{{ filteredResourceOptData.length }}</strong> 台 VM 需要调整
                &nbsp;·&nbsp; 可释放 CPU: <strong>{{ resourceOptSavings.cpu }} 核</strong>
                &nbsp;·&nbsp; 可释放内存: <strong>{{ resourceOptSavings.memory }} GB</strong>
              </span>
            </div>
            <div class="analysis-toolbar">
              <el-input v-model="rightsizeSearch" placeholder="搜索虚拟机" clearable class="search-input">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="mismatchTypeFilter" placeholder="错配类型" clearable class="filter-select" style="width:160px">
                <el-option label="全部类型" value="" />
                <el-option label="CPU富余/内存紧张" value="cpu_rich_memory_poor" />
                <el-option label="CPU不足/内存富余" value="cpu_poor_memory_rich" />
                <el-option label="双重过剩" value="both_underutilized" />
                <el-option label="双重超载" value="both_overutilized" />
                <el-option label="配比合理" value="balanced" />
              </el-select>
            </div>
            <div class="table-wrapper" :style="{ height: rightsizeTableHeight + 'px' }">
              <el-table :data="pagedResourceOptData" stripe v-loading="analysisLoading.resource"
                :height="rightsizeTableHeight" class="detail-table" row-key="vmName" style="min-width: 1400px">
                <el-table-column prop="vmName" label="虚拟机" min-width="160" show-overflow-tooltip />
                <el-table-column prop="cluster" label="集群" min-width="110" show-overflow-tooltip />
                <el-table-column prop="hostIp" label="主机IP" width="120" />
                <el-table-column label="当前CPU" width="90" align="center">
                  <template #default="{ row }">{{ row.currentCpu }} 核</template>
                </el-table-column>
                <el-table-column label="推荐CPU" width="90" align="center">
                  <template #default="{ row }">
                    <span :class="{ 'text-success': row.recommendedCpu < row.currentCpu, 'text-warning': row.recommendedCpu > row.currentCpu }">
                      {{ row.recommendedCpu }} 核
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="当前内存" width="100" align="center">
                  <template #default="{ row }">{{ row.currentMemoryGb }} GB</template>
                </el-table-column>
                <el-table-column label="推荐内存" width="100" align="center">
                  <template #default="{ row }">
                    <span :class="{ 'text-success': row.recommendedMemoryGb < row.currentMemoryGb, 'text-warning': row.recommendedMemoryGb > row.currentMemoryGb }">
                      {{ row.recommendedMemoryGb }} GB
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="P95 使用率" width="140">
                  <template #default="{ row }">
                    <div class="p95-cell">
                      <div>CPU: {{ row.cpuP95 }}% (均{{ row.cpuAvg }}%)</div>
                      <div>内存: {{ row.memoryP95 }}% (均{{ row.memoryAvg }}%)</div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="mismatchType" label="错配类型" width="150" align="center">
                  <template #default="{ row }">
                    <el-tag :type="getMismatchTypeTagType(row.mismatchType)" size="small">
                      {{ getMismatchTypeText(row.mismatchType) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="wasteRatio" label="浪费比例" width="90" align="center">
                  <template #default="{ row }">
                    <span :class="{ 'text-success': row.wasteRatio > 0, 'text-warning': row.wasteRatio < 0 }">
                      {{ row.wasteRatio > 0 ? '+' : '' }}{{ row.wasteRatio }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="adjustmentType" label="调整方向" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="getAdjustmentTypeTagType(row.adjustmentType)" size="small">
                      {{ getAdjustmentTypeText(row.adjustmentType) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="80" align="center">
                  <template #default="{ row }">
                    <el-progress :percentage="row.confidence" :color="getConfidenceColor(row.confidence)"
                      :show-text="false" :stroke-width="8" style="width:55px" />
                    <span class="confidence-text">{{ row.confidence }}%</span>
                  </template>
                </el-table-column>
                <el-table-column label="判断依据" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="reason-text">{{ row.reason }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="table-pagination" v-if="filteredResourceOptData.length > 0">
              <span class="pagination-total">共 {{ filteredResourceOptData.length }} 条</span>
              <el-pagination v-model:current-page="rightsizeCurrentPage" v-model:page-size="analysisPageSize"
                :page-sizes="logsPageSizes" :total="filteredResourceOptData.length" :layout="logsPaginationLayout"
                :size="paginationSize" />
            </div>
            <el-empty v-if="!analysisLoading.resource && filteredResourceOptData.length === 0" description="暂无资源优化数据" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.resource" @click="runAnalysis('resource')">开始分析</el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="闲置检测" name="idle">
          <!-- 闲置检测 - 分析结果 -->
          <div class="analysis-content analysis-idle" v-if="hasAnalysisResults.idle">
            <!-- 统计卡片 -->
            <div class="zombie-stats-row">
              <div class="zombie-stat-card stat-total">
                <div class="stat-icon-bg bg-orange">
                  <el-icon>
                    <Monitor />
                  </el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ analysisData.idle.length }}</div>
                  <div class="stat-label">闲置VM数量</div>
                </div>
              </div>
              <div class="zombie-stat-card stat-critical">
                <div class="stat-icon-bg bg-red">
                  <el-icon>
                    <Warning />
                  </el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ getIdleCountByRisk('critical') }}</div>
                  <div class="stat-label">严重风险</div>
                </div>
              </div>
              <div class="zombie-stat-card stat-high">
                <div class="stat-icon-bg bg-orange">
                  <el-icon>
                    <Warning />
                  </el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ getIdleCountByRisk('high') }}</div>
                  <div class="stat-label">高风险</div>
                </div>
              </div>
              <div class="zombie-stat-card stat-avg">
                <div class="stat-icon-bg bg-blue">
                  <el-icon>
                    <TrendCharts />
                  </el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ getAverageIdleDays() }}</div>
                  <div class="stat-label">平均闲置天数</div>
                </div>
              </div>
            </div>

            <!-- 表格区域 -->
            <div class="zombie-table-section">
              <!-- 工具栏 -->
              <div class="zombie-toolbar">
                <div class="toolbar-left">
                  <el-input v-model="zombieSearch" placeholder="搜索虚拟机名称、集群、主机IP..." clearable class="search-input"
                    prefix-icon="Search" />
                  <el-select v-model="idleTypeFilter" placeholder="闲置类型" clearable class="filter-select">
                    <el-option label="全部类型" value="" />
                    <el-option label="已关机" value="powered_off" />
                    <el-option label="开机闲置" value="idle_powered_on" />
                    <el-option label="低活跃" value="low_activity" />
                  </el-select>
                  <el-select v-model="riskLevelFilter" placeholder="风险等级" clearable class="filter-select">
                    <el-option label="全部等级" value="" />
                    <el-option label="严重" value="critical" />
                    <el-option label="高" value="high" />
                    <el-option label="中" value="medium" />
                    <el-option label="低" value="low" />
                  </el-select>
                </div>
                <div class="toolbar-right">
                  <el-button :icon="Refresh" @click="refreshIdleData" :loading="analysisLoading.idle">
                    刷新
                  </el-button>
                </div>
              </div>

              <!-- 表格 -->
              <div class="table-wrapper" :style="{ height: idleTableHeight + 'px' }">
                <el-table :data="pagedIdleData" stripe v-loading="analysisLoading.idle" :height="idleTableHeight"
                  class="detail-table zombie-table" :empty-text="filteredIdleData.length === 0 ? '未找到匹配的结果' : '暂无分析结果'"
                  flex style="min-width: 1100px">
                  <el-table-column prop="vmName" label="虚拟机" min-width="160" show-overflow-tooltip>
                    <template #default="{ row }">
                      <div class="vm-cell">
                        <el-icon class="vm-icon">
                          <Monitor />
                        </el-icon>
                        <span class="vm-name">{{ row.vmName }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="isIdle" label="状态" width="80" align="center">
                    <template #default="{ row }">
                      <el-tag :type="row.isIdle ? 'danger' : 'info'" size="small">
                        {{ row.isIdle ? '闲置' : '正常' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="cluster" label="集群" min-width="100" show-overflow-tooltip />
                  <el-table-column prop="hostIp" label="主机IP" width="120" show-overflow-tooltip />
                  <el-table-column prop="idleType" label="闲置类型" width="100" align="center">
                    <template #default="{ row }">
                      <el-tag :type="getIdleTypeTagType(row.idleType)" size="small">
                        {{ getIdleTypeText(row.idleType) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="riskLevel" label="风险等级" width="90" align="center">
                    <template #default="{ row }">
                      <div class="risk-cell">
                        <el-icon :class="getRiskIconClass(row.riskLevel)">
                          <component :is="getRiskIcon(row.riskLevel)" />
                        </el-icon>
                        <span>{{ getRiskLevelText(row.riskLevel) }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="daysInactive" label="闲置天数" width="90" align="center">
                    <template #default="{ row }">
                      <span :class="getDaysInactiveClass(row.daysInactive)">{{ row.daysInactive }} 天</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="lastActivityTime" label="最后活动" width="150" show-overflow-tooltip>
                    <template #default="{ row }">
                      <span class="activity-time">{{ formatLastActivityTime(row.lastActivityTime) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="confidence" label="置信度" width="80" align="center">
                    <template #default="{ row }">
                      <el-progress :percentage="row.confidence" :color="getConfidenceColor(row.confidence)"
                        :show-text="false" :stroke-width="6" />
                      <span class="confidence-text">{{ row.confidence }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="recommendation" label="优化建议" min-width="180" show-overflow-tooltip />
                </el-table>
              </div>

              <!-- 分页 -->
              <div class="table-pagination" v-if="filteredIdleData.length > 0">
                <span class="pagination-total">共 {{ filteredIdleData.length }} 条</span>
                <el-pagination v-model:current-page="zombieCurrentPage" v-model:page-size="analysisPageSize"
                  :page-sizes="logsPageSizes" :total="filteredIdleData.length" :layout="logsPaginationLayout"
                  :size="paginationSize" />
              </div>
            </div>
          </div>

          <!-- 空状态 - 分析尚未运行 -->
          <div v-else class="zombie-empty-state">
            <div class="empty-illustration">
              <div class="empty-icon-circle">
                <el-icon class="empty-main-icon">
                  <Monitor />
                </el-icon>
              </div>
            </div>
            <h3 class="empty-title">闲置检测分析</h3>
            <p class="empty-desc">识别长期低负载或已关机的闲置虚拟机，帮助您优化资源使用</p>
            <ul class="empty-features">
              <li><el-icon>
                  <Check />
                </el-icon> 检测已关机且长期未活动的虚拟机</li>
              <li><el-icon>
                  <Check />
                </el-icon> 识别开机但CPU/内存使用率极低的VM</li>
              <li><el-icon>
                  <Check />
                </el-icon> 分析闲置天数和风险等级</li>
              <li><el-icon>
                  <Check />
                </el-icon> 提供资源优化建议</li>
            </ul>
            <el-button type="primary" size="large" :loading="analysisLoading.idle" :icon="VideoPlay"
              @click="runAnalysis('idle')" class="run-analysis-btn">
              开始分析
            </el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="潮汐检测" name="tidal">
          <div class="analysis-content" v-if="hasAnalysisResults.resource && analysisData.tidal.length > 0">
            <div class="analysis-toolbar">
              <el-input v-model="tidalSearch" placeholder="搜索虚拟机名称、集群、主机IP..." clearable class="search-input">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="tidalGranularityFilter" placeholder="潮汐粒度" clearable class="filter-select" style="width:140px">
                <el-option label="全部粒度" value="" />
                <el-option label="周粒度" value="weekly" />
                <el-option label="月粒度" value="monthly" />
              </el-select>
              <el-button :icon="Refresh" @click="refreshResourceData" :loading="analysisLoading.resource">刷新</el-button>
            </div>
            <div class="table-wrapper" :style="{ height: tidalTableHeight + 'px' }">
              <el-table :data="pagedTidalData" stripe v-loading="analysisLoading.resource"
                :height="tidalTableHeight" class="detail-table" row-key="vmName" style="min-width: 1100px">
                <el-table-column prop="vmName" label="虚拟机" min-width="160" show-overflow-tooltip />
                <el-table-column prop="cluster" label="集群" min-width="100" show-overflow-tooltip />
                <el-table-column prop="hostIp" label="主机IP" width="120" />
                <el-table-column prop="tidalGranularity" label="潮汐粒度" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="row.tidalGranularity === 'monthly' ? 'warning' : 'primary'" size="small">
                      {{ row.tidalGranularity === 'monthly' ? '月粒度' : '周粒度' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="volatilityLevel" label="波动程度" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag :type="row.volatilityLevel === 'high' ? 'danger' : 'warning'" size="small">
                      {{ row.volatilityLevel === 'high' ? '高' : '中等' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="coefficientOfVariation" label="CV 变异系数" width="110" align="center">
                  <template #default="{ row }">{{ row.coefficientOfVariation?.toFixed(3) }}</template>
                </el-table-column>
                <el-table-column prop="peakValleyRatio" label="峰谷比" width="90" align="center">
                  <template #default="{ row }">{{ row.peakValleyRatio?.toFixed(1) }}</template>
                </el-table-column>
                <el-table-column label="建议关机时段" min-width="180" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ row.recommendedOffHours?.description || '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="分析依据" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="reason-text">{{ row.reason }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="table-pagination" v-if="filteredTidalData.length > 0">
              <span class="pagination-total">共 {{ filteredTidalData.length }} 条</span>
              <el-pagination v-model:current-page="tidalCurrentPage" v-model:page-size="analysisPageSize"
                :page-sizes="logsPageSizes" :total="filteredTidalData.length" :layout="logsPaginationLayout"
                :size="paginationSize" />
            </div>
          </div>
          <div v-else-if="hasAnalysisResults.resource && analysisData.tidal.length === 0" class="analysis-placeholder">
            <el-empty description="未检测到具有潮汐特征的虚拟机（需至少7天数据覆盖完整一周）" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="潮汐检测基于天级数据，支持周粒度（≥7天）和月粒度（≥30天）检测">
              <el-button type="primary" :loading="analysisLoading.resource" @click="runAnalysis('resource')">开始分析</el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="健康评分" name="health">
          <div class="analysis-content" v-if="hasAnalysisResults.health">
            <el-card v-loading="analysisLoading.health">
              <template #header>
                <div class="health-score-header">
                  <span class="health-score-title">平台健康评分</span>
                  <span class="health-score-value" :class="getHealthScoreClass(analysisData.health?.overallScore)">
                    {{ analysisData.health?.overallScore !== undefined ? analysisData.health.overallScore.toFixed(0) :
                      '-' }}
                  </span>
                </div>
              </template>
              <el-descriptions :column="2" border class="health-descriptions">
                <el-descriptions-item label="健康等级">
                  <el-tag :type="getHealthGradeTagType(analysisData.health?.grade)" size="large">
                    {{ getHealthGradeText(analysisData.health?.grade) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="集群数">{{ analysisData.health?.clusterCount ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="主机数">{{ analysisData.health?.hostCount ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="虚拟机数">{{ analysisData.health?.vmCount ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="资源均衡">
                  <el-progress :percentage="analysisData.health?.balanceScore ?? 0"
                    :color="getScoreColor(analysisData.health?.balanceScore)" :show-text="true" />
                </el-descriptions-item>
                <el-descriptions-item label="超配风险">
                  <el-progress :percentage="100 - (analysisData.health?.overcommitScore ?? 0)"
                    :color="getOvercommitScoreColor(analysisData.health?.overcommitScore)" :show-text="true" />
                </el-descriptions-item>
                <el-descriptions-item label="热点集中">
                  <el-progress :percentage="100 - (analysisData.health?.hotspotScore ?? 0)"
                    :color="getHotspotScoreColor(analysisData.health?.hotspotScore)" :show-text="true" />
                </el-descriptions-item>
              </el-descriptions>

              <!-- 发现的问题 -->
              <div v-if="analysisData.health?.findings && analysisData.health.findings.length > 0"
                class="health-findings">
                <h4>发现的问题</h4>
                <el-table :data="analysisData.health.findings" stripe class="detail-table">
                  <el-table-column prop="category" label="类别" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getFindingCategoryTagType(row.category)" size="small">
                        {{ getFindingCategoryText(row.category) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="severity" label="严重程度" width="90">
                    <template #default="{ row }">
                      <el-tag :type="getSeverityTagType(row.severity)" size="small">
                        {{ getSeverityText(row.severity) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
                </el-table>
              </div>

              <!-- 改进建议 -->
              <div v-if="analysisData.health?.recommendations && analysisData.health.recommendations.length > 0"
                class="health-recommendations">
                <h4>改进建议</h4>
                <ul>
                  <li v-for="(rec, index) in analysisData.health.recommendations" :key="index">{{ rec }}</li>
                </ul>
              </div>
            </el-card>
            <el-empty v-if="!analysisLoading.health && !analysisData.health" description="暂无分析结果" />
          </div>
          <div v-else class="analysis-placeholder">
            <el-empty description="该分析尚未运行">
              <el-button type="primary" :loading="analysisLoading.health" @click="runAnalysis('health')">
                开始分析
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="评估模式" name="analysisMode">
          <AnalysisModeTab v-if="task?.id" :task-id="task.id" :task-status="task.status" />
          <div v-else class="analysis-placeholder">
            <el-empty description="任务未完成，无法配置评估模式" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="任务配置" name="config">
          <div class="config-content">
            <el-card v-loading="!task">
              <template #header>
                <div class="config-header">
                  <el-icon>
                    <Setting />
                  </el-icon>
                  <span>任务配置信息</span>
                </div>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="任务名称">
                  {{ task?.name || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="任务类型">
                  <el-tag :type="task?.type === 'collection' ? 'primary' : 'success'" size="small">
                    {{ getTaskTypeText(task?.type) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="任务状态">
                  <el-tag :type="getStatusType(task?.status)" size="small">
                    {{ getStatusText(task?.status) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="平台类型">
                  {{ getPlatformText(task?.platform) }}
                </el-descriptions-item>
                <el-descriptions-item label="连接名称">
                  {{ task?.connectionName || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="连接主机">
                  {{ task?.connectionHost || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="评估对象数量">
                  {{ task?.selectedVMCount ?? '-' }} 台虚拟机
                </el-descriptions-item>
                <el-descriptions-item label="评估模式">
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <el-tag :type="analysisModeOptions.find(m => m.value === task?.config?.mode)?.type || 'info'"
                      size="small">
                      {{analysisModeOptions.find(m => m.value === task?.config?.mode)?.label || (task?.config?.mode ||
                        '-')}}
                    </el-tag>
                    <el-dropdown v-if="task?.status === 'completed'" trigger="click"
                      @command="(cmd) => handleModeChange(cmd)">
                      <el-button text size="small" style="padding: 0;">
                        <el-icon>
                          <Setting />
                        </el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item v-for="mode in analysisModeOptions" :key="mode.value" :command="mode.value"
                            :disabled="mode.value === task?.mode">
                            <el-tag :type="mode.type" size="small" style="margin-right: 8px;">
                              {{ mode.label }}
                            </el-tag>
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </el-descriptions-item>
                <el-descriptions-item label="采集天数">
                  {{ task?.config?.metricDays ?? '-' }} 天
                </el-descriptions-item>
                <el-descriptions-item label="开始时间">
                  {{ formatConfigTime(task?.startedAt) }}
                </el-descriptions-item>
                <el-descriptions-item label="完成时间" :span="task?.completedAt ? 1 : 2">
                  {{ formatConfigTime(task?.completedAt) }}
                </el-descriptions-item>
                <el-descriptions-item v-if="task?.completedAt" label="执行耗时">
                  {{ formatDuration(task) }}
                </el-descriptions-item>
              </el-descriptions>

              <!-- 选中的虚拟机列表 -->
              <div v-if="task?.selectedVMs && task.selectedVMs.length > 0" class="selected-vms-section">
                <div class="section-title">
                  <el-icon>
                    <Monitor />
                  </el-icon>
                  <span>选中的虚拟机 ({{ task.selectedVMs.length }})</span>
                </div>
                <div class="selected-vms-list">
                  <el-tag v-for="(vm, index) in displayedSelectedVMs" :key="index" size="small" class="vm-tag">
                    {{ vm }}
                  </el-tag>
                  <el-button v-if="task.selectedVMs.length > maxDisplayVMs" text size="small"
                    @click="showAllVMs = !showAllVMs">
                    {{ showAllVMs ? '收起' : `展开剩余 ${task.selectedVMs.length - maxDisplayVMs} 台` }}
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="虚拟机列表" name="vms">
          <div class="vms-content">
            <!-- 任务进行中提示 -->
            <div v-if="!task?.id" class="vm-list-placeholder">
              <el-empty description="任务执行中，虚拟机列表将在任务完成后显示">
                <template #image>
                  <el-icon :size="60" class="is-loading">
                    <Loading />
                  </el-icon>
                </template>
              </el-empty>
            </div>
            <!-- 虚拟机列表 -->
            <template v-else>
              <div class="table-toolbar">
                <el-input v-model="vmSearch" placeholder="搜索虚拟机" prefix-icon="Search" clearable style="width: 300px"
                  @input="handleVMSearch" />
                <div class="table-stats">
                  共 {{ vmTotal }} 台虚拟机
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="vmList" stripe :loading="vmListLoading" height="400" style="min-width: 800px">
                  <el-table-column prop="name" label="虚拟机名称" min-width="180" />
                  <el-table-column prop="cpuCount" label="CPU" width="100">
                    <template #default="{ row }">
                      {{ row.cpuCount > 0 ? row.cpuCount + ' 核' : '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="memoryGb" label="内存" width="120">
                    <template #default="{ row }">
                      {{ row.memoryGb > 0 ? row.memoryGb + ' GB' : '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="powerState" label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getPowerStateType(row.powerState)" size="small">
                        {{ getPowerStateText(row.powerState) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="datacenter" label="数据中心" width="150" />
                  <el-table-column prop="hostIp" label="主机IP" width="150" />
                </el-table>
              </div>
              <div class="table-pagination">
                <span class="pagination-total">共 {{ vmTotal }} 条</span>
                <el-pagination v-model:current-page="vmCurrentPage" v-model:page-size="vmPageSize"
                  :page-sizes="vmPageSizes" :total="vmTotal" :layout="vmPaginationLayout"
                  :size="paginationSize"
                  @current-change="handleVMPageChange" @size-change="handleVMSizeChange" />
              </div>
            </template>
          </div>
        </el-tab-pane>

        <el-tab-pane label="执行日志" name="logs">
          <div class="analysis-content">
            <!-- 工具栏：级别筛选、搜索和刷新 -->
            <div class="logs-toolbar">
              <div class="logs-filters">
                <!-- 日志级别筛选 -->
                <el-select v-model="selectedLogLevels" placeholder="选择日志级别" multiple collapse-tags collapse-tags-tooltip
                  clearable class="log-level-select" @change="onLogsFilterChange">
                  <el-option label="全部" value="" />
                  <el-option label="Debug" value="debug" />
                  <el-option label="Info" value="info" />
                  <el-option label="Warning" value="warn" />
                  <el-option label="Error" value="error" />
                </el-select>
                <!-- 关键字搜索 -->
                <el-input v-model="logsSearchText" placeholder="搜索日志内容..." clearable class="search-input"
                  @input="onLogsSearchChange">
                  <template #prefix>
                    <el-icon>
                      <Search />
                    </el-icon>
                  </template>
                </el-input>
              </div>
              <div class="logs-actions">
                <el-button size="small" :disabled="!task?.id" @click="manualRefreshLogs" :loading="logsLoading">
                  <el-icon>
                    <Refresh />
                  </el-icon>
                  刷新
                </el-button>
              </div>
            </div>

            <el-empty v-if="!task?.id" description="该任务没有后端任务ID，无法查询执行日志" />

            <!-- 日志表格区域 -->
            <div v-else class="logs-content">
              <div class="table-wrapper" :style="{ height: logsTableHeight + 'px' }">
                <el-table :data="paginatedLogs" stripe v-loading="logsLoading" :height="logsTableHeight"
                  class="detail-table" :default-sort="{ prop: 'timestamp', order: 'descending' }">
                  <el-table-column prop="timestamp" label="时间" width="180" sortable>
                    <template #default="{ row }">
                      {{ formatLogTimestamp(row.timestamp) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="level" label="级别" width="100">
                    <template #default="{ row }">
                      <el-tag :type="getLogLevelType(row.level)" size="small">
                        {{ row.level.toUpperCase() }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="message" label="内容" min-width="400" show-overflow-tooltip />
                  <!-- 空数据提示 -->
                  <template #empty>
                    <el-empty v-if="!logsLoading" description="暂无执行日志" />
                  </template>
                </el-table>
              </div>

              <!-- 分页 -->
              <div class="table-pagination">
                <span class="pagination-total">共 {{ logsTotal }} 条</span>
                <el-pagination v-model:current-page="logsCurrentPage" v-model:page-size="logsPageSize"
                  :page-sizes="logsPageSizes" :total="logsTotal" :layout="logsPaginationLayout"
                  :size="paginationSize" />
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 任务失败状态 -->
    <div v-else-if="task?.status === 'failed'" class="failed-state">
      <el-card class="failed-card">
        <div class="failed-icon">
          <el-icon :size="80">
            <CircleClose />
          </el-icon>
        </div>
        <h2 class="failed-title">任务执行失败</h2>
        <p class="failed-message">{{ task.error || '未知错误' }}</p>

        <div class="failed-details" v-if="task.connectionName || task.connectionHost">
          <div class="detail-item">
            <span class="detail-label">连接名称:</span>
            <span class="detail-value">{{ task.connectionName || '-' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">主机地址:</span>
            <span class="detail-value">{{ task.connectionHost || '-' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">平台类型:</span>
            <span class="detail-value">{{ task.platform === 'vcenter' ? 'VMware vSphere' : 'H3C UIS' }}</span>
          </div>
        </div>

        <div class="failed-actions">
          <el-button @click="router.push('/')">
            返回首页
          </el-button>
          <el-button type="primary" :disabled="!task?.id" @click="handleRetry">
            <el-icon>
              <Refresh />
            </el-icon>
            重试任务
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeMount, onMounted, onUnmounted, reactive, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore, type Task } from '@/stores/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as TaskAPI from '@/api/task'
import type { TaskMode } from '@/api/task'
import * as ReportAPI from '@/api/report'
import * as AnalysisAPI from '@/api/analysis'
import * as ResourceAPI from '@/api/resource'
import AnalysisModeTab from './AnalysisModeTab.vue'
import {
  ArrowLeft,
  Download,
  MoreFilled,
  VideoPause,
  VideoPlay,
  CloseBold,
  DataAnalysis,
  CircleCheck,
  CircleClose,
  Loading,
  Search,
  DocumentCopy,
  Notebook,
  Delete,
  Setting,
  Monitor,
  Refresh,
  Warning,
  TrendCharts,
  Check
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

function goHome() {
  router.push('/')
}

// 使用 computed 确保 taskId 随路由变化而更新
const taskId = computed(() => route.params.id as string)

const activeTab = ref('overview')
const vmSearch = ref('')
const zombieSearch = ref('')
const idleTypeFilter = ref('')
const riskLevelFilter = ref('')
const rightsizeSearch = ref('')
const tidalSearch = ref('')
const mismatchTypeFilter = ref('')
const tidalGranularityFilter = ref('')
const vmList = ref<any[]>([])
const vmListLoading = ref(false)
const vmTotal = ref(0)
const vmCurrentPage = ref(1)
const vmPageSize = ref(50)
const zombieCurrentPage = ref(1)
const rightsizeCurrentPage = ref(1)
const tidalCurrentPage = ref(1)

// 分析结果Tab状态
const analysisSummaryData = ref<any>(null)
const analysisSummaryLoading = ref(false)
const summaryOptimizations = reactive({ resource: true, idle: true })
const analysisPageSize = ref(20)
const taskLogs = ref<any[]>([])
const allLogs = ref<any[]>([])  // 存储所有日志（用于过滤）
const logsLoading = ref(false)
const logsTotal = ref(0)
const logsCurrentPage = ref(1)
const logsPageSize = ref(30)
const logsSearchText = ref('')
const selectedLogLevels = ref<string[]>([])  // 日志级别筛选
const showAllVMs = ref(false)  // 是否显示所有选中的VM
const maxDisplayVMs = 20  // 最多显示多少个VM
const windowHeight = ref(window.innerHeight)
const windowWidth = ref(window.innerWidth)
const pollTimer = ref<number | null>(null)
const pollTimeout = ref<number | null>(null)
let vmSearchTimer: number | null = null

// 报告相关状态
const exporting = reactive({
  xlsx: false,
  pdf: false
})
const reportHistory = ref<any[]>([])
const reportsLoading = ref(false)

const isCompactWindow = computed(() => windowHeight.value <= 700 || windowWidth.value <= 1100)
const paginationSize = computed(() => isCompactWindow.value ? 'small' : 'default')

// 各表格独立高度
const idleTableHeight = 380        // 闲置检测表格
const rightsizeTableHeight = 380  // 资源配置优化表格
const tidalTableHeight = 380       // 使用模式表格
const logsTableHeight = 380        // 执行日志表格
const vmPaginationLayout = computed(() =>
  isCompactWindow.value ? 'sizes, prev, pager, next' : 'sizes, prev, pager, next, jumper'
)
const logsPaginationLayout = computed(() =>
  isCompactWindow.value ? 'sizes, prev, pager, next' : 'sizes, prev, pager, next, jumper'
)
const vmPageSizes = computed(() => (isCompactWindow.value ? [10, 20, 50, 100] : [20, 50, 100, 200]))
const logsPageSizes = computed(() => (isCompactWindow.value ? [10, 20, 30, 50] : [10, 15, 30, 50, 100]))

const analysisLoading = reactive({
  idle: false,
  resource: false,
  health: false
})

// 本地状态：跟踪哪些分析已完成（用于控制 Tab 显示）
// 直接使用后端字段名：idle, resource, health
const hasAnalysisResults = reactive({
  idle: false,
  resource: false,
  health: false
})

// 评估模式相关
const analysisModeOptions = [
  { value: 'safe' as const, label: '安全模式', type: 'success' },
  { value: 'saving' as const, label: '节省模式', type: 'primary' },
  { value: 'aggressive' as const, label: '激进模式', type: 'danger' },
  { value: 'custom' as const, label: '自定义模式', type: 'info' }
]

// 分析数据存储 - 使用后端返回的字段结构
const analysisData = reactive<{
  idle: AnalysisAPI.IdleResult[]
  resourceOptimization: any[]
  tidal: any[]
  health: AnalysisAPI.HealthScoreResult | null
}>({
  idle: [],
  resourceOptimization: [],
  tidal: [],
  health: null
})

const task = computed(() => taskStore.getTask(Number(taskId.value)))

// 调试：监听 task 变化
watch(task, (newTask) => {
  console.log('[TaskDetail] task changed:', newTask)
  console.log('[TaskDetail] task.analysisResults:', newTask?.analysisResults)
}, { immediate: true, deep: true })

// 分析项类型定义
interface AnalysisItem {
  key: 'idle' | 'rightsize' | 'health'
  title: string
  description: string
  icon: string
  color: string
}

const analyses: AnalysisItem[] = [
  { key: 'idle', title: '闲置检测', description: '识别长期低负载或已关机的虚拟机', icon: 'Monitor', color: 'orange' },
  { key: 'rightsize', title: '资源优化', description: '资源配置优化与潮汐模式分析', icon: 'TrendCharts', color: 'blue' },
  { key: 'health', title: '健康评分', description: '平台健康度评估', icon: 'DataAnalysis', color: 'purple' }
]

const completedAnalyses = computed(() => {
  return Object.values(hasAnalysisResults).filter(v => v).length
})

// 显示的选中VM列表（支持展开/收起）
const displayedSelectedVMs = computed(() => {
  if (!task.value?.selectedVMs) return []
  if (showAllVMs.value) return task.value.selectedVMs
  return task.value.selectedVMs.slice(0, maxDisplayVMs)
})

// 映射前端 Tab key 到 hasAnalysisResults 的键
// 前端 Tab key：zombie, rightsize, tidal, health
// hasAnalysisResults 键：idle, resource, health
function getAnalysisStatus(analysisKey: string): boolean {
  const keyMapping: Record<string, 'idle' | 'resource' | 'health'> = {
    idle: 'idle',
    rightsize: 'resource',
    tidal: 'resource',
    health: 'health'
  }
  const hasKey = keyMapping[analysisKey]
  return hasKey ? hasAnalysisResults[hasKey] : false
}

// 检查分析是否正在加载
function isAnalysisLoading(analysisKey: string): boolean {
  const loadingMapping: Record<string, 'idle' | 'resource' | 'health'> = {
    idle: 'idle',
    rightsize: 'resource',
    tidal: 'resource',
    health: 'health'
  }
  const loadingKey = loadingMapping[analysisKey]
  return loadingKey ? analysisLoading[loadingKey] : false
}

function matchByKeyword(row: any, keyword: string, fields: string[]) {
  if (!keyword) return true
  const q = keyword.toLowerCase().trim()
  return fields.some((field) => String(row?.[field] ?? '').toLowerCase().includes(q))
}

// 闲置检测 (Idle) Tab 过滤 - 支持关键字、类型和风险等级筛选
const filteredIdleData = computed(() => {
  return analysisData.idle.filter((row) => {
    // 关键字筛选
    if (!matchByKeyword(row, zombieSearch.value, ['vmName', 'cluster', 'hostIp', 'recommendation'])) {
      return false
    }
    // 闲置类型筛选
    if (idleTypeFilter.value && row.idleType !== idleTypeFilter.value) {
      return false
    }
    // 风险等级筛选
    if (riskLevelFilter.value && row.riskLevel !== riskLevelFilter.value) {
      return false
    }
    return true
  })
})

// 资源优化 Tab 过滤
const filteredResourceOptData = computed(() => {
  return analysisData.resourceOptimization.filter((row) => {
    if (!matchByKeyword(row, rightsizeSearch.value, ['vmName', 'cluster', 'hostIp'])) return false
    if (mismatchTypeFilter.value && row.mismatchType !== mismatchTypeFilter.value) return false
    return true
  })
})

// 潮汐检测 Tab 过滤
const filteredTidalData = computed(() => {
  return analysisData.tidal.filter((row) => {
    if (!matchByKeyword(row, tidalSearch.value, ['vmName', 'cluster', 'hostIp'])) return false
    if (tidalGranularityFilter.value && row.tidalGranularity !== tidalGranularityFilter.value) return false
    return true
  })
})

// 资源优化 - 可释放CPU/内存汇总
const resourceOptSavings = computed(() => {
  const data = filteredResourceOptData.value
  const cpu = data.reduce((sum: number, row: any) => {
    const diff = (row.currentCpu || 0) - (row.recommendedCpu || 0)
    return sum + (diff > 0 ? diff : 0)
  }, 0)
  const memory = data.reduce((sum: number, row: any) => {
    const diff = (row.currentMemoryGb || 0) - (row.recommendedMemoryGb || 0)
    return sum + (diff > 0 ? diff : 0)
  }, 0)
  return { cpu, memory: memory.toFixed(1) }
})

const pagedIdleData = computed(() => {
  const start = (zombieCurrentPage.value - 1) * analysisPageSize.value
  return filteredIdleData.value.slice(start, start + analysisPageSize.value)
})

const pagedResourceOptData = computed(() => {
  const start = (rightsizeCurrentPage.value - 1) * analysisPageSize.value
  return filteredResourceOptData.value.slice(start, start + analysisPageSize.value)
})

const pagedTidalData = computed(() => {
  const start = (tidalCurrentPage.value - 1) * analysisPageSize.value
  return filteredTidalData.value.slice(start, start + analysisPageSize.value)
})

// 初始化任务数据
async function initTaskData(preserveTabState = false) {
  // 重置状态
  stopPolling()
  // 保留 Tab 状态，避免在刷新任务时跳转到其他 Tab
  if (!preserveTabState) {
    activeTab.value = 'overview'
  }
  vmSearch.value = ''
  zombieSearch.value = ''
  rightsizeSearch.value = ''
  tidalSearch.value = ''
  vmList.value = []
  vmTotal.value = 0
  vmCurrentPage.value = 1
  zombieCurrentPage.value = 1
  rightsizeCurrentPage.value = 1
  tidalCurrentPage.value = 1
  taskLogs.value = []
  allLogs.value = []
  analysisData.idle = []
  analysisData.resourceOptimization = []
  analysisData.tidal = []
  analysisData.health = null

  // 如果没有有效的 taskId，不执行后续操作
  if (!taskId.value) {
    console.log('[TaskDetail] 无效的 taskId')
    return
  }

  // 详细日志：输出任务信息用于诊断
  console.log('[TaskDetail] 初始化任务详情, taskId:', taskId.value)
  console.log('[TaskDetail] task.value:', task.value)

  if (!task.value) {
    ElMessage.error('任务不存在')
    router.push('/')
    return
  }

  console.log('[TaskDetail] 任务详情:', {
    id: task.value.id,
    connectionId: task.value.connectionId,
    status: task.value.status,
    selectedVMs: task.value.selectedVMs?.length
  })

  // 根据后端的 analysisResults 初始化 hasAnalysisResults
  // 后端返回 { idle, resource, health }，前端使用 { zombie, rightsize, tidal, health }
  if (task.value.analysisResults) {
    console.log('[TaskDetail] 初始化 hasAnalysisResults:', task.value.analysisResults)
    // 直接使用后端字段名：idle, resource, health
    hasAnalysisResults.idle = task.value.analysisResults.idle || false
    hasAnalysisResults.resource = task.value.analysisResults.resource || false
    hasAnalysisResults.health = task.value.analysisResults.health || false
    console.log('[TaskDetail] hasAnalysisResults 已更新:', hasAnalysisResults)
  }

  // 始终从后端同步最新数据，确保显示的是最新状态
  // 因为用户可能在任务列表停留了一段时间，此时任务状态可能已经变化
  console.log('[TaskDetail] 从后端同步最新任务数据')
  await syncTaskFromBackend()

  // 重新检查 task 是否存在（可能在 async 操作后失效）
  if (!task.value) {
    console.error('[TaskDetail] syncTaskFromBackend 后 task 变成 undefined')
    return
  }

  // 只有在任务已完成或有后端任务ID时才加载虚拟机列表
  // 任务进行中时，虚拟机列表会在任务完成后通过快照获取
  if (task.value.id) {
    console.log('[TaskDetail] 有id，加载VM列表:', task.value.id)
    await loadVMList()
  } else {
    console.log('[TaskDetail] 没有id，无法加载VM列表')
  }

  if (task.value.id) {
    await loadTaskLogs()
    await loadAnalysisResultFromBackend(task.value.id)
    pollTaskStatus(task.value.id)
    // 如果任务已完成，也加载报告历史
    if (task.value.status === 'completed') {
      await loadReportHistory()
    }
  }
}

// 在组件挂载之前就停止全局轮询，避免与 TaskDetail 的轮询冲突
onBeforeMount(() => {
  console.log('[TaskDetail] onBeforeMount: 停止全局轮询')
  taskStore.stopPolling()
})

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)

  await initTaskData()
})

// 监听 taskId 变化，重新加载数据
watch(taskId, () => {
  initTaskData()
})

watch(zombieSearch, () => {
  zombieCurrentPage.value = 1
})

watch(rightsizeSearch, () => {
  rightsizeCurrentPage.value = 1
})

watch(tidalSearch, () => {
  tidalCurrentPage.value = 1
})

watch(analysisPageSize, () => {
  zombieCurrentPage.value = 1
  rightsizeCurrentPage.value = 1
  tidalCurrentPage.value = 1
})

// 监听标签页切换，刷新对应的数据
watch(activeTab, async (newTab) => {
  console.log('[TaskDetail] 切换标签页:', newTab)

  // 每次切换标签时，先同步一次最新的任务状态
  // 这样确保用户看到的数据是最新的
  if (task.value?.id) {
    try {
      const taskInfo = await TaskAPI.getTask(task.value.id)
      // 使用 updateTask 方法确保响应式更新
      taskStore.updateTask(task.value.id, {
        status: taskInfo.status,
        progress: taskInfo.progress,
        error: taskInfo.error,
        startedAt: taskInfo.startedAt,
        completedAt: taskInfo.completedAt
      })
    } catch (error) {
      console.error('[TaskDetail] 同步任务状态失败:', error)
    }
  }

  // 根据切换到的标签页，刷新对应的数据
  switch (newTab) {
    case 'overview':
      console.log('[TaskDetail] 切换到概览标签')
      // 概览数据在 initTaskData 时已经加载
      break
    case 'vms':
      console.log('[TaskDetail] 切换到虚拟机标签')
      await loadVMList()
      break
    case 'logs':
      console.log('[TaskDetail] 切换到执行日志标签')
      await loadTaskLogs()  // 刷新日志
      break
    case 'analysis':
      console.log('[TaskDetail] 切换到分析结果标签')
      if (task.value?.id) {
        await fetchAnalysisSummary()
      }
      break
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  stopPolling()
})

function handleWindowResize() {
  windowHeight.value = window.innerHeight
  windowWidth.value = window.innerWidth
}

async function loadVMList() {
  await loadTaskVMs()
}

async function loadTaskVMs() {
  if (!task.value?.id) {
    console.log('[TaskDetail] loadTaskVMs: 没有id')
    return
  }

  console.log('[TaskDetail] loadTaskVMs: 开始加载, id=', task.value.id)
  vmListLoading.value = true
  try {
    const offset = (vmCurrentPage.value - 1) * vmPageSize.value
    console.log('[TaskDetail] 调用 listTaskVMs, params:', {
      id: task.value.id,
      limit: vmPageSize.value,
      offset,
      keyword: vmSearch.value
    })
    const result = await TaskAPI.listTaskVMs(
      task.value.id,
      vmPageSize.value,
      offset,
      vmSearch.value
    )
    console.log('[TaskDetail] listTaskVMs 返回结果:', result)
    vmList.value = result.vms || []
    vmTotal.value = result.total || 0
    console.log('[TaskDetail] VM列表加载完成, 数量:', vmList.value.length, '总数:', vmTotal.value)
  } catch (error: any) {
    const errorMsg = error?.message || error?.toString() || '未知错误'
    console.error('[TaskDetail] 加载任务快照失败:', errorMsg)
    console.error('[TaskDetail] 错误详情:', error)

    // 如果任务快照不存在，尝试从连接的数据库加载
    if (task.value?.connectionId) {
      console.log('[TaskDetail] 快照不存在，尝试从connectionId加载虚拟机, connectionId=', task.value.connectionId)
      try {
        const vmResult = await ResourceAPI.getVMs(task.value.connectionId, {
          search: vmSearch.value,
          size: vmPageSize.value,
          page: vmCurrentPage.value
        })
        vmList.value = vmResult.items || []
        vmTotal.value = vmResult.total || 0
        console.log('[TaskDetail] 从connectionId加载VM成功, 数量:', vmList.value.length)
      } catch (e: any) {
        console.error('[TaskDetail] 从数据库加载虚拟机列表失败:', e)
        vmList.value = []
        vmTotal.value = 0
      }
    } else {
      console.log('[TaskDetail] 没有connectionId，无法加载虚拟机')
      vmList.value = []
      vmTotal.value = 0
    }
  } finally {
    vmListLoading.value = false
  }
}

function handleVMPageChange(page: number) {
  vmCurrentPage.value = page
  loadTaskVMs()
}

function handleVMSizeChange(size: number) {
  vmPageSize.value = size
  vmCurrentPage.value = 1
  loadTaskVMs()
}

function handleVMSearch() {
  vmCurrentPage.value = 1
  if (vmSearchTimer) {
    clearTimeout(vmSearchTimer)
  }
  vmSearchTimer = window.setTimeout(() => {
    loadTaskVMs()
  }, 300)
}

function stopPolling() {
  if (pollTimer.value !== null) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  if (pollTimeout.value !== null) {
    clearTimeout(pollTimeout.value)
    pollTimeout.value = null
  }
}

function pollTaskStatus(id: number) {
  console.log('[TaskDetail] pollTaskStatus 开始轮询任务状态, taskId:', id)
  stopPolling()

  let logRefreshCounter = 0  // 日志刷新计数器：任务运行中每 5 次轮询（10秒）刷新一次日志
  let pollCount = 0  // 轮询计数器，用于诊断

  pollTimer.value = window.setInterval(async () => {
    const pollStart = Date.now()
    pollCount++
    console.log(`[TaskDetail] 轮询 #${pollCount} 开始`, { taskId: id, time: new Date().toLocaleTimeString() })

    try {
      const taskInfo = await TaskAPI.getTask(id)
      const pollElapsed = Date.now() - pollStart
      console.log(`[TaskDetail] 轮询 #${pollCount} 完成`, {
        taskId: id,
        status: taskInfo.status,
        progress: taskInfo.progress,
        elapsed: `${pollElapsed}ms`
      })

      // 使用 updateTask 方法确保响应式更新
      taskStore.updateTask(id, {
        status: taskInfo.status,
        progress: taskInfo.progress,
        error: taskInfo.error,
        startedAt: taskInfo.startedAt,
        completedAt: taskInfo.completedAt
      })

      // 任务运行中时，每 5 次轮询刷新一次日志（每 10 秒）
      if (taskInfo.status === 'running') {
        logRefreshCounter++
        if (logRefreshCounter >= 5) {
          console.log('[TaskDetail] pollTaskStatus 自动刷新日志, taskId:', id)
          await loadTaskLogs()  // 静默刷新，不显示提示
          logRefreshCounter = 0
        }
      } else if (taskInfo.status === 'completed') {
        console.log('[TaskDetail] pollTaskStatus 任务完成, 停止轮询, taskId:', id)
        stopPolling()
        const storeTask = taskStore.getTask(Number(taskId.value))
        if (storeTask?.connectionId) {
          await loadVMList()
        }
        await loadTaskLogs()
        await loadAnalysisResultFromBackend(id)
      } else if (taskInfo.status === 'failed') {
        console.log('[TaskDetail] pollTaskStatus 任务失败, 停止轮询, taskId:', id, 'error:', taskInfo.error)
        stopPolling()
        await loadTaskLogs()
        ElMessage.error('任务执行失败: ' + (taskInfo.error || '未知错误'))
      }
    } catch (error) {
      console.error('[TaskDetail] pollTaskStatus 轮询任务状态失败:', error)
    }
  }, 5000)

  pollTimeout.value = window.setTimeout(() => {
    console.log('[TaskDetail] pollTaskStatus 轮询超时, 停止轮询, taskId:', id)
    stopPolling()
  }, 5 * 60 * 1000)
}

async function handleCancel() {
  console.log('[TaskDetail] handleCancel 用户请求取消任务, taskId:', taskId.value)
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '确认取消', { type: 'warning' })

    console.log('[TaskDetail] handleCancel 用户确认取消, 调用 store.cancelTask')
    await taskStore.cancelTask(Number(taskId.value))
    ElMessage.success('任务已取消')
    console.log('[TaskDetail] handleCancel 取消成功, 返回首页')
    router.push('/')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消任务失败')
    }
  }
}

async function handleRetry() {
  console.log('[TaskDetail] handleRetry 用户请求重试任务, taskId:', task.value?.id)

  if (!task.value?.id) {
    console.warn('[TaskDetail] handleRetry 任务无效，无法重试')
    ElMessage.warning('该任务没有后端任务ID，无法重试')
    return
  }

  try {
    console.log('[TaskDetail] handleRetry 调用 retryTask API, taskId:', task.value.id)
    const newTaskId = await TaskAPI.retryTask(task.value.id)
    console.log('[TaskDetail] handleRetry 重试成功, newTaskId:', newTaskId)

    // 刷新任务列表
    await taskStore.syncTasksFromBackend()
    // 跳转到新任务页面
    router.push('/task/' + newTaskId)
    ElMessage.success('任务已提交重试')
  } catch (error: any) {
    ElMessage.error(error.message || '重试失败')
  }
}

// 加载日志（静默，不显示成功提示）
async function loadTaskLogs() {
  if (!task.value?.id) return

  logsLoading.value = true
  try {
    // 获取所有日志数据
    const logs = await TaskAPI.getTaskLogs(task.value.id)
    allLogs.value = logs

    // 应用搜索过滤
    applyLogFilter()
  } catch (error: any) {
    ElMessage.error(error.message || '获取任务日志失败')
  } finally {
    logsLoading.value = false
  }
}

// 手动刷新日志（带成功提示）
async function manualRefreshLogs() {
  await loadTaskLogs()
  ElMessage.success(`刷新成功，共 ${logsTotal.value} 条记录`)
}

// 应用搜索过滤（支持级别筛选和关键字搜索）
function applyLogFilter() {
  let filteredLogs = allLogs.value

  // 级别筛选
  if (selectedLogLevels.value.length > 0) {
    filteredLogs = filteredLogs.filter((log: any) =>
      selectedLogLevels.value.includes(log.level)
    )
  }

  // 关键字搜索
  if (logsSearchText.value) {
    const searchLower = logsSearchText.value.toLowerCase()
    filteredLogs = filteredLogs.filter((log: any) =>
      log.message?.toLowerCase().includes(searchLower) ||
      log.level?.toLowerCase().includes(searchLower)
    )
  }

  taskLogs.value = filteredLogs
  logsTotal.value = filteredLogs.length

  // 如果当前页超过总页数，重置到第一页
  const maxPage = Math.ceil(filteredLogs.length / logsPageSize.value) || 1
  if (logsCurrentPage.value > maxPage) {
    logsCurrentPage.value = 1
  }
}

// 日志级别筛选变化时重新过滤
function onLogsFilterChange() {
  logsCurrentPage.value = 1
  applyLogFilter()
}

// 分页后的日志数据
const paginatedLogs = computed(() => {
  const start = (logsCurrentPage.value - 1) * logsPageSize.value
  const end = start + logsPageSize.value
  return taskLogs.value.slice(start, end)
})

// 日志级别对应的 Tag 类型
function getLogLevelType(level: string) {
  const levelMap: Record<string, string> = {
    'error': 'danger',
    'warn': 'warning',
    'warning': 'warning',
    'info': 'info',
    'debug': 'info',
    'success': 'success',
    'system': 'info'
  }
  return levelMap[level] || 'info'
}

// 防抖搜索
function onLogsSearchChange() {
  if (vmSearchTimer) {
    clearTimeout(vmSearchTimer)
  }
  vmSearchTimer = window.setTimeout(() => {
    logsCurrentPage.value = 1 // 重置到第一页
    applyLogFilter()  // 只过滤，不重新请求
  }, 300)
}

async function loadAnalysisResultFromBackend(id: number) {
  console.log('[loadAnalysisResultFromBackend] 开始加载分析结果, id:', id)
  try {
    // 并行获取所有分析结果
    const [idleResult, resourceResult, healthResult] = await Promise.allSettled([
      AnalysisAPI.getIdleResults(id).catch(() => []),
      AnalysisAPI.getResourceResults(id).catch(() => ({ resourceOptimization: [], tidal: [], summary: {} })),
      AnalysisAPI.getHealthResults(id).catch(() => null)
    ])

    // 处理闲置检测结果
    if (idleResult.status === 'fulfilled' && idleResult.value.length > 0) {
      analysisData.idle = idleResult.value
      hasAnalysisResults.idle = true
      console.log('[loadAnalysisResultFromBackend] idle 结果加载完成, 数量:', idleResult.value.length)
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 idle 数据')
    }

    // 处理资源分析结果
    if (resourceResult.status === 'fulfilled' && resourceResult.value) {
      const rv = resourceResult.value as any
      analysisData.resourceOptimization = rv.resourceOptimization || []
      analysisData.tidal = rv.tidal || []
      if (analysisData.resourceOptimization.length > 0 || analysisData.tidal.length > 0) {
        hasAnalysisResults.resource = true
      }
      console.log('[loadAnalysisResultFromBackend] resource 结果加载完成, resourceOptimization:', analysisData.resourceOptimization.length, 'tidal:', analysisData.tidal.length)
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 resource 数据')
    }

    // 处理健康评分结果
    if (healthResult.status === 'fulfilled' && healthResult.value) {
      analysisData.health = healthResult.value
      hasAnalysisResults.health = true
      console.log('[loadAnalysisResultFromBackend] health 结果加载完成')
    } else {
      console.log('[loadAnalysisResultFromBackend] 未找到 health 数据')
    }

  } catch (error) {
    console.error('[loadAnalysisResultFromBackend] 加载失败:', error)
  }
}

function getDefaultAnalysisConfig(type: string) {
  if (type === 'idle') {
    return {
      analysisDays: 30,
      cpuThreshold: 5,
      memoryThreshold: 10,
      minConfidence: 60
    }
  }
  if (type === 'rightsize') {
    return {
      analysisDays: 30,
      bufferRatio: 0.2
    }
  }
  if (type === 'tidal') {
    return {
      analysisDays: 30,
      minStability: 0.6
    }
  }
  return {}
}

async function runAnalysis(type: string) {
  console.log('[runAnalysis] 开始执行分析:', type)

  // 检查是否有有效的评估任务ID
  const assessmentTaskId = task.value?.id
  if (!assessmentTaskId) {
    console.warn('[runAnalysis] 缺少评估任务ID (id)')
    ElMessage.warning('缺少评估任务信息，无法执行分析')
    return
  }

  // 映射前端 Tab 类型到后端 API 类型和 loading 状态类型
  const loadingTypeMapping: Record<string, 'idle' | 'resource' | 'health'> = {
    idle: 'idle',
    rightsize: 'resource',
    tidal: 'resource',
    health: 'health'
  }
  const loadingType = loadingTypeMapping[type]
  analysisLoading[loadingType] = true

  try {
    ElMessage.info('正在执行分析...')

    // 不发送 config，让后端从任务配置中读取自定义配置
    // 这样可以支持用户在 AnalysisModeTab 中修改的自定义配置
    const config = undefined

    // 根据类型调用不同的 API
    if (type === 'idle') {
      const results = await AnalysisAPI.runIdleAnalysis(assessmentTaskId, config)
      analysisData.idle = results
      hasAnalysisResults.idle = true
      ElMessage.success(`闲置检测完成，发现 ${results.length} 条结果`)
    } else if (type === 'rightsize' || type === 'tidal') {
      const results = await AnalysisAPI.runResourceAnalysis(assessmentTaskId, config)
      const rv = results as any
      analysisData.resourceOptimization = rv.resourceOptimization || []
      analysisData.tidal = rv.tidal || []
      hasAnalysisResults.resource = true
      const totalCount = (analysisData.resourceOptimization.length || 0) + (analysisData.tidal.length || 0)
      ElMessage.success(`资源分析完成，发现 ${totalCount} 条结果`)
    } else if (type === 'health') {
      const result = await AnalysisAPI.runHealthAnalysis(assessmentTaskId, config)
      analysisData.health = result
      hasAnalysisResults.health = true
      ElMessage.success(`健康评分完成，评分: ${result.overallScore?.toFixed(0) || 0}`)
    }

  } catch (error: any) {
    console.error('[runAnalysis] 分析失败:', error)
    ElMessage.error(error.response?.data?.error?.message || error.message || '分析执行失败')
  } finally {
    analysisLoading[loadingType] = false
  }
}

async function handleModeChange(newMode: TaskMode) {
  try {
    const modeLabel = analysisModeOptions.find(m => m.value === newMode)?.label || newMode
    await ElMessageBox.confirm(
      `确定要将评估模式修改为"${modeLabel}"并重新评估吗？`,
      '确认修改模式',
      { type: 'warning' }
    )
    await TaskAPI.updateTaskMode(Number(taskId.value), newMode)
    ElMessage.success('模式已修改，正在重新评估...')
    await taskStore.syncTasksFromBackend()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '修改模式失败')
    }
  }
}

async function handleCommand(cmd: string) {
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除此任务吗？', '确认删除', { type: 'warning' })
      stopPolling()
      taskStore.deleteTask(Number(taskId.value))
      ElMessage.success('任务已删除')
      router.push('/')
    } catch {
      // 用户取消
    }
  } else if (cmd === 'reEvaluate') {
    try {
      await ElMessageBox.confirm(
        '重新评估将使用当前数据重新运行分析，是否继续？',
        '确认重新评估',
        { type: 'info' }
      )
      await TaskAPI.reEvaluateTask(Number(taskId.value))
      ElMessage.success('重新评估已启动')
      // 刷新任务状态
      await taskStore.syncTasksFromBackend()
    } catch (e: any) {
      if (e !== 'cancel') {
        ElMessage.error(e.message || '重新评估失败')
      }
    }
  }
}

async function exportReport(format: 'xlsx' | 'pdf' = 'xlsx') {
  if (!task.value?.id) {
    ElMessage.warning('缺少任务信息，无法导出报告')
    return
  }

  try {
    exporting[format] = true
    const formatName = format === 'xlsx' ? 'Excel' : 'PDF'
    ElMessage.info(`正在生成${formatName}报告...`)

    // 使用正确的 API：generateReport 需要的 format 是 'excel' 或 'pdf'
    const apiFormat = format === 'xlsx' ? 'excel' : 'pdf'
    await ReportAPI.generateReport(task.value.id, { format: apiFormat })

    ElMessage.success(`${formatName}报告已生成`)
    // 刷新报告列表
    await loadReportHistory()
  } catch (error: any) {
    ElMessage.error('导出失败: ' + (error.response?.data?.error?.message || error.message || '未知错误'))
  } finally {
    exporting[format] = false
  }
}


// 加载报告历史
async function loadReportHistory() {
  // 使用 taskId.value 而不是 task.value?.id，确保一致性
  if (!task.value?.id) return

  try {
    reportsLoading.value = true
    console.log('[TaskDetail] 加载报告历史, taskId:', task.value.id)
    const reports = await ReportAPI.getTaskReports(task.value.id)
    console.log('[TaskDetail] 报告列表加载成功:', reports)
    reportHistory.value = reports
  } catch (error: any) {
    console.error('加载报告列表失败:', error)
    ElMessage.error('加载报告列表失败: ' + (error.message || '未知错误'))
  } finally {
    reportsLoading.value = false
  }
}

// 下载报告
async function downloadReport(report: any) {
  try {
    // 生成友好的文件名：任务名_时间.扩展名
    const taskName = task.value?.name || 'report'
    const timeStr = report.createdAt ? new Date(report.createdAt).getTime() : Date.now()
    const ext = report.format === 'excel' ? 'xlsx' : 'pdf'
    const filename = `${taskName}_${timeStr}.${ext}`

    await ReportAPI.downloadReportFile(report.id, filename)
    ElMessage.success('报告已下载')
  } catch (error: any) {
    ElMessage.error('下载失败: ' + (error.message || '未知错误'))
  }
}

// 删除报告
async function deleteReport(report: any) {
  try {
    await ElMessageBox.confirm('确定要删除此报告吗？此操作无法撤销。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })

    await ReportAPI.deleteReport(report.id)
    ElMessage.success('报告已删除')

    // 刷新列表
    await loadReportHistory()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

function getStatusType(status: string | undefined) {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    paused: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return typeMap[status || ''] || 'info'
}

function getStatusText(status: string | undefined) {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return textMap[status || ''] || '-'
}

function formatMemory(mb: number): string {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(1) + ' GB'
  }
  return mb + ' MB'
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(i > 0 ? 1 : 0) + ' ' + sizes[i]
}

// 格式化报告创建时间
function formatReportTime(isoTime: string): string {
  if (!isoTime) return '-'
  const date = new Date(isoTime)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`

  // 超过7天显示具体日期
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const mins = date.getMinutes().toString().padStart(2, '0')
  return `${month}-${day} ${hours}:${mins}`
}

// 获取评估模式标签
function getModeLabel(mode: TaskMode | undefined): string {
  const modeLabels: Record<TaskMode, string> = {
    safe: '安全',
    saving: '节省',
    aggressive: '激进',
    custom: '自定义'
  }
  return mode ? modeLabels[mode] || mode : '节省'
}

function formatDuration(taskData: Task | undefined): string {
  if (!taskData?.startedAt) return '-'
  // 任务进行中时不显示耗时，避免实时计算导致持续增长
  if (taskData.status === 'pending' || taskData.status === 'running') {
    return '进行中...'
  }
  if (!taskData.completedAt) return '-'
  const start = new Date(taskData.startedAt).getTime()
  const end = new Date(taskData.completedAt).getTime()
  const duration = end - start
  const seconds = Math.floor(duration / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    const mins = minutes % 60
    return hours + '小时' + (mins > 0 ? mins + '分钟' : '')
  }
  if (minutes > 0) {
    const secs = seconds % 60
    return minutes + '分钟' + (secs > 0 ? secs + '秒' : '')
  }
  return seconds + '秒'
}

// ============ 分析结果辅助函数 ============

// 闲置类型相关
function getIdleTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    'powered_off': '已关机',
    'idle_powered_on': '开机闲置',
    'low_activity': '低活跃'
  }
  return typeMap[type] || '未知'
}

function getIdleTypeTagType(type: string): string {
  const tagMap: Record<string, string> = {
    'powered_off': 'info',
    'idle_powered_on': 'warning',
    'low_activity': 'success'
  }
  return tagMap[type] || 'info'
}

// 风险等级相关
function getRiskLevelText(level: string): string {
  const levelMap: Record<string, string> = {
    'critical': '严重',
    'high': '高',
    'medium': '中',
    'low': '低'
  }
  return levelMap[level] || '未知'
}

function getRiskLevelTagType(level: string): string {
  const tagMap: Record<string, string> = {
    'critical': 'danger',
    'high': 'warning',
    'medium': 'info',
    'low': 'info'
  }
  return tagMap[level] || 'info'
}

// 闲置检测 - 按风险等级统计数量
function getIdleCountByRisk(riskLevel: string): number {
  return analysisData.idle.filter(item => item.riskLevel === riskLevel).length
}

// 闲置检测 - 计算平均闲置天数
function getAverageIdleDays(): number {
  if (analysisData.idle.length === 0) return 0
  const totalDays = analysisData.idle.reduce((sum, item) => sum + (item.daysInactive || 0), 0)
  return Math.round(totalDays / analysisData.idle.length)
}

// 闲置检测 - 刷新数据
async function refreshIdleData() {
  if (!task.value?.id) return
  analysisLoading.idle = true
  try {
    const results = await AnalysisAPI.getIdleResults(task.value.id)
    analysisData.idle = results
    ElMessage.success(`刷新成功，共 ${results.length} 条记录`)
  } catch (error: any) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  } finally {
    analysisLoading.idle = false
  }
}

// 资源优化/潮汐检测 - 刷新数据
async function refreshResourceData() {
  if (!task.value?.id) return
  analysisLoading.resource = true
  try {
    const rv = await AnalysisAPI.getResourceResults(task.value.id)
    analysisData.resourceOptimization = rv.resourceOptimization || []
    analysisData.tidal = rv.tidal || []
    ElMessage.success(`刷新成功，资源优化 ${analysisData.resourceOptimization.length} 条，潮汐 ${analysisData.tidal.length} 条`)
  } catch (error: any) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  } finally {
    analysisLoading.resource = false
  }
}

// 闲置检测 - 获取风险图标
function getRiskIcon(riskLevel: string): string {
  const iconMap: Record<string, string> = {
    'critical': 'CircleClose',
    'high': 'Warning',
    'medium': 'Warning',
    'low': 'CircleCheck'
  }
  return iconMap[riskLevel] || 'Warning'
}

// 闲置检测 - 获取风险图标样式类
function getRiskIconClass(riskLevel: string): string {
  const classMap: Record<string, string> = {
    'critical': 'risk-icon-critical',
    'high': 'risk-icon-high',
    'medium': 'risk-icon-medium',
    'low': 'risk-icon-low'
  }
  return classMap[riskLevel] || 'risk-icon-medium'
}

// 闲置检测 - 获取闲置天数样式类
function getDaysInactiveClass(days: number): string {
  if (days >= 90) return 'days-critical'
  if (days >= 60) return 'days-high'
  if (days >= 30) return 'days-medium'
  return 'days-normal'
}

// 闲置检测 - 格式化最后活动时间
function formatLastActivityTime(timestamp: string | null): string {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return '今天'
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays} 天前`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} 周前`

    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return '-'
  }
}

// 闲置检测 - 获取置信度颜色
function getConfidenceColor(confidence: number): string {
  if (confidence >= 80) return '#67c23a'
  if (confidence >= 60) return '#409eff'
  if (confidence >= 40) return '#e6a23c'
  return '#f56c6c'
}

// 分析结果 - 获取汇总数据
async function fetchAnalysisSummary() {
  if (!task.value?.id) return
  const opts: string[] = []
  if (summaryOptimizations.resource && hasAnalysisResults.resource) opts.push('resource')
  if (summaryOptimizations.idle && hasAnalysisResults.idle) opts.push('idle')
  if (opts.length === 0) {
    analysisSummaryData.value = null
    return
  }
  analysisSummaryLoading.value = true
  try {
    const result = await AnalysisAPI.getAnalysisSummary(task.value.id, opts.join(','))
    analysisSummaryData.value = result
  } catch (error: any) {
    ElMessage.error('获取分析汇总失败: ' + (error.message || '未知错误'))
  } finally {
    analysisSummaryLoading.value = false
  }
}

// 潮汐粒度文本
function getTidalGranularityText(granularity: string): string {
  const map: Record<string, string> = {
    daily: '日粒度',
    weekly: '周粒度',
    monthly: '月粒度'
  }
  return map[granularity] || granularity || '未知'
}

// 调整类型相关
function getAdjustmentTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    'down_significant': '大幅缩减',
    'down': '缩减',
    'none': '配置合理',
    'up': '扩容',
    'up_significant': '大幅扩容'
  }
  return typeMap[type] || '未知'
}

function getAdjustmentTypeTagType(type: string): string {
  const tagMap: Record<string, string> = {
    'down_significant': 'success',
    'down': 'success',
    'none': 'info',
    'up': 'warning',
    'up_significant': 'danger'
  }
  return tagMap[type] || 'info'
}

// 使用模式相关（后端实际返回值：stable/tidal/burst/unknown）
function getUsagePatternText(pattern: string): string {
  const patternMap: Record<string, string> = {
    'stable': '稳定',
    'tidal': '潮汐',
    'burst': '突发',
    'unknown': '未知'
  }
  return patternMap[pattern] || '未知'
}

function getUsagePatternTagType(pattern: string): string {
  const tagMap: Record<string, string> = {
    'stable': 'success',
    'tidal': 'primary',
    'burst': 'warning',
    'unknown': 'info'
  }
  return tagMap[pattern] || 'info'
}

// 波动性相关
function getVolatilityLevelText(level: string): string {
  const levelMap: Record<string, string> = {
    'low': '低',
    'moderate': '中',
    'high': '高',
    'unknown': '未知'
  }
  return levelMap[level] || '未知'
}

function getVolatilityLevelTagType(level: string): string {
  const tagMap: Record<string, string> = {
    'low': 'success',
    'moderate': 'warning',
    'high': 'danger',
    'unknown': 'info'
  }
  return tagMap[level] || 'info'
}

// 配置错配相关
function getMismatchTypeText(type: string): string {
  const typeMap: Record<string, string> = {
    'cpu_rich_memory_poor': 'CPU富足/内存不足',
    'cpu_poor_memory_rich': 'CPU不足/内存富足',
    'both_underutilized': '均利用不足',
    'both_overutilized': '均利用过高',
    'balanced': '配比合理'
  }
  return typeMap[type] || '未知'
}

function getMismatchTypeTagType(type: string): string {
  const tagMap: Record<string, string> = {
    'cpu_rich_memory_poor': 'warning',
    'cpu_poor_memory_rich': 'warning',
    'both_underutilized': 'info',
    'both_overutilized': 'danger',
    'balanced': 'success'
  }
  return tagMap[type] || 'info'
}

// 健康评分相关
function getHealthGradeText(grade: string): string {
  const gradeMap: Record<string, string> = {
    'excellent': '优秀',
    'good': '良好',
    'fair': '一般',
    'poor': '较差',
    'critical': '危急',
    'no_data': '无数据'
  }
  return gradeMap[grade] || '未知'
}

function getHealthGradeTagType(grade: string): string {
  const tagMap: Record<string, string> = {
    'excellent': 'success',
    'good': 'primary',
    'fair': 'warning',
    'poor': 'danger',
    'critical': 'danger',
    'no_data': 'info'
  }
  return tagMap[grade] || 'info'
}

function getHealthScoreClass(score: number | undefined): string {
  if (score === undefined) return ''
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-fair'
  return 'score-poor'
}

function getScoreColor(score: number | undefined): string {
  if (score === undefined) return '#909399'
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

function getOvercommitScoreColor(score: number | undefined): string {
  // 超配分数越高风险越大，颜色相反
  if (score === undefined) return '#909399'
  if (score <= 30) return '#67c23a'
  if (score <= 60) return '#e6a23c'
  return '#f56c6c'
}

function getHotspotScoreColor(score: number | undefined): string {
  // 热点分数越高风险越大，颜色相反
  if (score === undefined) return '#909399'
  if (score <= 30) return '#67c23a'
  if (score <= 60) return '#e6a23c'
  return '#f56c6c'
}

// 发现问题相关
function getFindingCategoryText(category: string): string {
  const categoryMap: Record<string, string> = {
    'overcommit': '超配',
    'balance': '负载均衡',
    'hotspot': '热点'
  }
  return categoryMap[category] || '其他'
}

function getFindingCategoryTagType(category: string): string {
  const tagMap: Record<string, string> = {
    'overcommit': 'warning',
    'balance': 'primary',
    'hotspot': 'danger'
  }
  return tagMap[category] || 'info'
}

// 严重程度相关（后端实际返回值：high/critical/severe）
function getSeverityText(severity: string): string {
  const severityMap: Record<string, string> = {
    'high': '高',
    'critical': '严重',
    'severe': '极严重'
  }
  return severityMap[severity] || '未知'
}

function getSeverityTagType(severity: string): string {
  const tagMap: Record<string, string> = {
    'high': 'warning',
    'critical': 'danger',
    'severe': 'danger'
  }
  return tagMap[severity] || 'info'
}

// 从后端同步任务信息（使用详情接口获取完整数据）
async function syncTaskFromBackend() {
  if (!taskId.value) {
    console.warn('[TaskDetail] 无效的 taskId，跳过同步')
    return
  }

  try {
    console.log('[TaskDetail] 从后端获取任务详情, taskId:', taskId.value)
    // 直接调用详情接口，获取完整数据
    const taskDetail = await TaskAPI.getTaskDetail(Number(taskId.value))
    console.log('[TaskDetail] 获取到任务详情:', {
      id: taskDetail.id,
      status: taskDetail.status,
      progress: taskDetail.progress,
      hasSelectedVMs: !!taskDetail.selectedVMs,
      hasConfig: !!taskDetail.config
    })

    // 更新 store 中的任务数据
    const storeTask = taskStore.getTask(Number(taskId.value))
    if (storeTask) {
      // 使用 updateTask 确保响应式更新（对象替换）
      taskStore.updateTask(Number(taskId.value), taskDetail)
      console.log('[TaskDetail] 已更新 store 中的任务数据')
    } else {
      // store 中没有该任务，添加新任务
      taskStore.tasks.push(taskDetail)
      console.log('[TaskDetail] 已添加新任务到 store')
    }

    // 同步更新 hasAnalysisResults
    // 直接使用后端字段名：idle, resource, health
    if (taskDetail.analysisResults) {
      hasAnalysisResults.idle = taskDetail.analysisResults.idle || false
      hasAnalysisResults.resource = taskDetail.analysisResults.resource || false
      hasAnalysisResults.health = taskDetail.analysisResults.health || false
      console.log('[TaskDetail] 已更新 hasAnalysisResults:', hasAnalysisResults)
    }
  } catch (e: any) {
    console.error('[TaskDetail] 同步后端任务失败:', e)
    if (e.response?.status === 404) {
      ElMessage.error('任务不存在')
      router.push('/')
    }
  }
}

function getPowerStateType(state: string) {
  const typeMap: Record<string, string> = {
    'poweredon': 'success',
    'poweredOn': 'success',
    'poweredoff': 'info',
    'poweredOff': 'info',
    'suspended': 'warning'
  }
  return typeMap[state] || 'info'
}

function getPowerStateText(state: string) {
  const textMap: Record<string, string> = {
    'poweredon': '开机',
    'poweredOn': '开机',
    'poweredoff': '关机',
    'poweredOff': '关机',
    'suspended': '挂起'
  }
  return textMap[state] || '未知'
}

function getTaskTypeText(type: string | undefined) {
  const typeMap: Record<string, string> = {
    collection: '数据采集',
    analysis: '数据分析'
  }
  return typeMap[type || ''] || '-'
}

function getPlatformText(platform: string | undefined) {
  const platformMap: Record<string, string> = {
    vcenter: 'VMware vCenter',
    'h3c-uis': 'H3C UIS'
  }
  return platformMap[platform || ''] || '-'
}

// 格式化日志时间戳
function formatLogTimestamp(timestamp: string): string {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return timestamp
  }
}

// 格式化配置时间
function formatConfigTime(timestamp: string | undefined): string {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return timestamp
  }
}
</script>

<style scoped lang="scss">
.task-detail-page {
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
  padding: $spacing-xl;
  box-sizing: border-box;
  overflow: hidden;
}

.completed-state {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.task-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  :deep(.el-tabs__content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.el-tab-pane) {
    height: 100%;
    min-height: 0;
  }
}

.task-header {
  display: grid;
  grid-template-columns: 40px 1fr 40px;
  align-items: center;
  gap: $spacing-md;

  .header-left {
    display: flex;
    justify-content: start;
  }

  .header-center {
    display: flex;
    align-items: center;
    justify-content: center;

    .task-title {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $spacing-md;

      h1 {
        font-size: 20px;
        font-weight: 600;
        margin: 0;
        display: flex;
        align-items: center;
        gap: $spacing-sm;
        text-align: center;
      }
    }
  }

  .header-right {
    display: flex;
    gap: $spacing-sm;
    justify-self: end;
  }
}

// 运行中状态
.running-state {
  padding: 20px;

  .running-card {
    max-width: 600px;
    margin: 0 auto;
  }

  .running-header {
    text-align: center;
    margin-bottom: 30px;
  }

  .running-icon {
    color: var(--el-color-primary);
    margin-bottom: 16px;
  }

  .running-title {
    font-size: 24px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: var(--el-text-color-primary);
  }

  .running-step {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0;
  }

  .running-progress {
    margin: 30px 0;
  }

  .running-stats {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin: 24px 0;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .stat-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .stat-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .running-actions {
    display: flex;
    justify-content: center;
    margin-top: 24px;
  }
}

// 暂停状态
.paused-state {
  padding: 20px;

  .paused-card {
    max-width: 600px;
    margin: 0 auto;
  }

  .paused-header {
    text-align: center;
    margin-bottom: 30px;
  }

  .paused-icon {
    color: var(--el-color-warning);
    margin-bottom: 16px;
  }

  .paused-title {
    font-size: 24px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: var(--el-text-color-primary);
  }

  .paused-step {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0;
  }

  .paused-progress {
    margin: 30px 0;
  }

  .paused-stats {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin: 24px 0;
  }

  .paused-actions {
    display: flex;
    justify-content: center;
    margin-top: 24px;
  }
}

// 失败状态
.failed-state {
  padding: 20px;

  .failed-card {
    max-width: 500px;
    margin: 0 auto;
    padding: 40px;
    text-align: center;
  }

  .failed-icon {
    color: var(--el-color-danger);
    margin-bottom: 20px;
  }

  .failed-title {
    font-size: 24px;
    font-weight: 600;
    margin: 0 0 12px 0;
    color: var(--el-text-color-primary);
  }

  .failed-message {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0 0 24px 0;
    line-height: 1.6;
  }

  .failed-details {
    background: var(--el-fill-color-light);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 24px;
    text-align: left;
  }

  .detail-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);

    &:last-child {
      border-bottom: none;
    }
  }

  .detail-label {
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .detail-value {
    color: var(--el-text-color-primary);
    font-size: 13px;
    font-weight: 500;
  }

  .failed-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
  }
}

// 完成横幅
.completion-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #f0f9ff 0%, #e8f5e9 100%);
  border: 1px solid rgba(103, 194, 58, 0.2);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;

  .cb-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .cb-icon {
    color: var(--el-color-success);
  }

  .cb-text {
    .cb-title {
      font-size: 18px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin-bottom: 4px;
    }

    .cb-sub {
      font-size: 13px;
      color: var(--el-text-color-secondary);
      display: flex;
      align-items: center;
      gap: 8px;

      .cb-platform {
        color: var(--el-color-primary);
        font-weight: 500;
      }

      .cb-conn {
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .cb-divider-inline {
        color: var(--el-border-color);
      }
    }
  }

  .cb-right {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .cb-stat {
    text-align: center;
  }

  .cbs-value {
    display: block;
    font-size: 24px;
    font-weight: 600;
    color: var(--el-color-primary);
    line-height: 1;
    margin-bottom: 4px;
  }

  .cbs-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .cb-divider {
    width: 1px;
    height: 32px;
    background: var(--el-border-color);
  }
}

.overview-grid {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px;
  min-height: 0;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;

  .o-ribbon {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #f4f9ff 0%, #ffffff 50%, #f4f9ff 100%);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 8px;
    padding: 12px 24px;
    flex-shrink: 0;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.08);

    &::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-image:
        linear-gradient(rgba(64, 158, 255, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(64, 158, 255, 0.05) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
      z-index: 0;
    }

    &::after {
      content: "";
      position: absolute;
      top: 0;
      right: 20%;
      width: 150px;
      height: 100px;
      background: radial-gradient(circle, rgba(64, 158, 255, 0.15) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }

    >* {
      position: relative;
      z-index: 1;
    }

    .r-left {
      display: flex;
      align-items: center;
      gap: 14px;

      .p-logo {
        font-size: 26px;
        color: #409eff;
        background: #ecf5ff;
        border: 1px solid #b3d8ff;
        padding: 8px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 10px rgba(64, 158, 255, 0.1) inset;
      }

      .p-title {
        font-size: 15px;
        font-weight: bold;
        color: #303133;
        margin-bottom: 2px;
        letter-spacing: 0.5px;
      }

      .p-sub {
        font-size: 12px;
        color: #909399;
        display: flex;
        align-items: center;
        gap: 8px;

        .p-sep {
          color: var(--el-border-color);
        }
      }
    }

    .r-right {
      display: flex;
      align-items: center;
      gap: 24px;

      .r-stat {
        display: flex;
        align-items: baseline;
        gap: 6px;

        .r-val {
          font-size: 20px;
          font-weight: bold;
          color: #409eff;
          line-height: 1;
          text-shadow: 0 0 8px rgba(64, 158, 255, 0.3);

          small {
            font-size: 13px;
            color: #909399;
            font-weight: normal;
          }
        }

        .r-lbl {
          font-size: 12px;
          color: #606266;
          margin-top: 3px;
        }
      }

      .r-div {
        width: 1px;
        height: 24px;
        background: rgba(64, 158, 255, 0.2);
      }
    }
  }

  .o-main {
    flex: 1;
    display: grid;
    grid-template-columns: 1.5fr 1fr;
    gap: 12px;
    min-height: 0;
  }

  .o-panel {
    background: var(--el-bg-color-overlay);
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    min-height: 0;

    .panel-hd {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--el-border-color-lighter);
      flex-shrink: 0;

      .ph-title {
        font-size: 14px;
        font-weight: bold;
        color: var(--el-text-color-primary);
        display: flex;
        align-items: center;
        gap: 6px;
      }

    }
  }

  .o-analysis {
    .o-list {
      min-height: 0;
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .o-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 6px;
      border: 1px solid var(--el-border-color-lighter);
      transition: all 0.2s;
      cursor: pointer;

      &:hover {
        background: var(--el-color-primary-light-9);
        border-color: var(--el-color-primary-light-7);
      }

      &.is-done {
        background: var(--el-color-success-light-9);
        border-color: var(--el-color-success-light-7);
        cursor: default;
      }

      &.is-loading {
        background: var(--el-color-info-light-9);
        border-color: var(--el-color-info-light-7);
        cursor: wait;
      }

      &.is-done:hover,
      &.is-loading:hover {
        background: var(--el-color-success-light-9);
        border-color: var(--el-color-success-light-7);
      }

      .i-icon {
        font-size: 18px;
        padding: 8px;
        border-radius: 6px;
        background: var(--el-bg-color);

        &.i-blue {
          color: var(--el-color-primary);
        }

        &.i-green {
          color: var(--el-color-success);
        }

        &.i-orange {
          color: var(--el-color-warning);
        }

        &.i-danger,
        &.i-purple {
          color: var(--el-color-danger);
        }
      }

      .i-core {
        flex: 1;
        min-width: 0;

        .i-name {
          font-size: 13px;
          font-weight: bold;
          color: var(--el-text-color-primary);
          margin-bottom: 2px;
        }

        .i-desc {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .i-act {
        flex-shrink: 0;
      }
    }
  }

  .o-report {
    padding: 0;

    .o-actions {
      padding: 16px;
      display: flex;
      gap: 12px;
      border-bottom: 1px dashed var(--el-border-color-lighter);

      .exp-btn {
        flex: 1;
        height: 36px;
        margin: 0;

        &.ex-excel {
          color: var(--el-color-primary);
          background: var(--el-color-primary-light-9);
          border-color: var(--el-color-primary-light-7);

          &:hover {
            background: var(--el-color-primary);
            color: white;
          }
        }

        &.ex-pdf {
          color: var(--el-color-success);
          background: var(--el-color-success-light-9);
          border-color: var(--el-color-success-light-7);

          &:hover {
            background: var(--el-color-success);
            color: white;
          }
        }
      }
    }

    .o-history {
      padding: 16px;
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;

      .hist-label {
        font-size: 12px;
        font-weight: bold;
        color: var(--el-text-color-secondary);
        margin-bottom: 10px;
      }

      .hist-list {
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
        overflow-y: auto;
      }

      .h-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px;
        background: var(--el-fill-color-light);
        border: 1px solid var(--el-border-color-lighter);
        border-radius: 6px;

        .h-fmt {
          font-size: 10px;
          font-weight: bold;
          padding: 2px 6px;
          border-radius: 4px;

          &.fmt-ex {
            background: var(--el-color-primary-light-9);
            color: var(--el-color-primary);
          }

          &.fmt-pd {
            background: var(--el-color-success-light-9);
            color: var(--el-color-success);
          }
        }

        .h-info {
          flex: 1;
          min-width: 0;

          .h-name {
            font-size: 12px;
            color: var(--el-text-color-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 2px;
          }

          .h-time {
            font-size: 11px;
            color: var(--el-text-color-secondary);
          }
        }

        .h-actions {
          display: flex;
          gap: 6px;
          opacity: 0;
          transition: opacity 0.2s;

          .h-btn {
            margin: 0;
          }
        }

        &:hover .h-actions {
          opacity: 1;
        }
      }

      .hist-empty {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px dashed var(--el-border-color-lighter);
        border-radius: 6px;

        .he-text {
          font-size: 12px;
          color: var(--el-text-color-placeholder);
        }
      }
    }
  }

  .history-table-wrapper {
    min-height: 260px;
  }
}

.vms-content {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .vm-list-placeholder {
    padding: 60px 0;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .table-toolbar {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-bottom: 12px;
    gap: $spacing-sm;

    .search-input {
      width: 300px;
      max-width: 100%;
    }

  }

  .table-wrapper {
    border: 1px solid $border-color-light;
    border-radius: 8px;
    overflow: hidden;
    overflow-x: auto;
  }

  .table-wrapper :deep(.el-table) {
    width: 100%;
  }

  .table-wrapper :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
}

.analysis-content {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .table-wrapper {
    border: 1px solid $border-color-light;
    border-radius: 8px;
    overflow: hidden;
    overflow-x: auto;
  }

  .table-wrapper :deep(.el-table) {
    width: 100%;
  }

  .table-wrapper :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }

  :deep(.el-table) {
    border: none;
  }

  :deep(.el-table th) {
    padding: 8px 0;
  }

  :deep(.el-table td) {
    padding: 7px 0;
  }

  .placeholder {
    padding: $spacing-xl;
    text-align: center;
    color: $text-color-secondary;
  }

  .analysis-toolbar {
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 12px;

    .search-input {
      width: 300px;
      max-width: 100%;
    }
  }

  .logs-toolbar {
    margin-bottom: 12px;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: $spacing-sm;

    .search-input {
      width: 300px;
      max-width: 100%;
    }

    .logs-actions {
      margin-left: auto;
      display: inline-flex;
      align-items: center;
    }
  }

  .logs-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

}

// ============ 统一分页器样式 ============

.table-pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 12px;
  gap: 12px;
  flex-wrap: wrap;

  .pagination-total {
    color: var(--el-text-color-secondary);
    font-size: 13px;
    white-space: nowrap;
  }

  :deep(.el-pagination) {
    justify-content: flex-end;
    flex-wrap: wrap;
    row-gap: 6px;
  }
}

.analysis-placeholder {
  padding: $spacing-xl 0;
}

// 资源优化汇总栏
.rightsize-summary-bar {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 8px 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);

  .rs-summary-text strong {
    color: var(--el-color-primary);
  }
}

// 判断依据文本
.reason-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

// 推荐关机时段文本
.off-hours-text {
  color: var(--el-color-warning);
  font-weight: 500;
  font-size: 13px;
}

// P95数据展示
.p95-cell {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

// 分析结果Tab
.analysis-summary-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
  overflow-y: auto;

  .summary-top-panel {
    display: grid;
    grid-template-columns: 1fr 220px 1fr;
    gap: 16px;
    flex-shrink: 0;
  }

  .summary-panel {
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    padding: 16px;
    background: var(--el-fill-color-blank);

    .summary-panel-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--el-border-color-lighter);
    }
  }

  .summary-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;

    .summary-metric-item {
      text-align: center;
      padding: 10px;
      background: var(--el-fill-color-light);
      border-radius: 6px;

      .sm-value {
        font-size: 22px;
        font-weight: 700;
        color: var(--el-text-color-primary);
        line-height: 1.2;
      }

      .sm-label {
        font-size: 11px;
        color: var(--el-text-color-secondary);
        margin-top: 4px;
      }

      &.highlight .sm-value {
        font-size: 24px;
      }
    }
  }

  .text-success {
    color: var(--el-color-success) !important;
  }

  .text-primary {
    color: var(--el-color-primary) !important;
  }

  .summary-controls {
    display: flex;
    flex-direction: column;

    .summary-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;

      .summary-checkbox {
        height: auto;
        align-items: flex-start;

        .checkbox-label {
          font-size: 13px;
          font-weight: 500;
        }
      }
    }

    .summary-calc-btn {
      margin-top: 16px;
      width: 100%;
    }
  }

  .summary-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 20px;
    color: var(--el-text-color-secondary);
  }

  .summary-empty-hint {
    text-align: center;
    color: var(--el-text-color-secondary);
    font-size: 13px;
    padding: 20px 0;
  }

  .summary-hosts-section {
    flex: 1;
    min-height: 200px;
    display: flex;
    flex-direction: column;

    .summary-hosts-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .summary-no-hosts {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

// 健康评分样式
.health-score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .health-score-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .health-score-value {
    font-size: 32px;
    font-weight: bold;
    padding: 8px 24px;
    border-radius: 8px;

    &.score-excellent {
      color: #67c23a;
      background: #f0f9ff;
    }

    &.score-good {
      color: #409eff;
      background: #ecf5ff;
    }

    &.score-fair {
      color: #e6a23c;
      background: #fdf6ec;
    }

    &.score-poor {
      color: #f56c6c;
      background: #fef0f0;
    }
  }
}

.health-descriptions {
  margin-bottom: 20px;
}

.health-findings {
  margin-top: 24px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin-bottom: 12px;
  }
}

.health-recommendations {
  margin-top: 20px;
  padding: 16px;
  background: var(--el-color-warning-light-9);
  border-radius: 8px;
  border-left: 4px solid var(--el-color-warning);

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin-bottom: 12px;
  }

  ul {
    margin: 0;
    padding-left: 20px;

    li {
      margin-bottom: 8px;
      color: var(--el-text-color-regular);
      line-height: 1.6;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}

// 文字颜色辅助类
.text-success {
  color: var(--el-color-success);
}

.text-warning {
  color: var(--el-color-warning);
}

// 资源配置优化表格单元格样式
.config-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;

  div {
    line-height: 1.4;
  }
}

.p95-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-regular);

  div {
    line-height: 1.4;
  }
}

.confidence-text {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.text-danger {
  color: var(--el-color-danger);
}

// 配置页面样式
.config-content {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .config-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }

  .selected-vms-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--el-border-color-lighter);

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin-bottom: 12px;
    }

    .selected-vms-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;

      .vm-tag {
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
}

// 日志工具栏增强样式
.logs-toolbar {
  .logs-filters {
    display: flex;
    gap: 12px;
    align-items: center;

    .log-level-select {
      width: 180px;
    }
  }
}

:deep(.report-history-dialog) {
  .el-dialog__header {
    margin-right: 0;
    padding-bottom: 10px;
  }

  .el-dialog__body {
    padding-top: 6px;
  }
}

@media (max-width: 768px),
(max-height: 500px) {
  .task-detail-page {
    padding: 10px;
    gap: 8px;
  }

  .task-header {
    grid-template-columns: 1fr auto;

    .header-left {
      display: none;
    }

    .header-center .task-title h1 {
      font-size: 18px;
      margin-bottom: 0;
    }
  }

  .vms-content {
    .table-toolbar {
      flex-wrap: wrap;
      align-items: flex-start;

      .search-input {
        width: 300px;
        max-width: 100%;
      }
    }

  }

  .analysis-content {
    .logs-toolbar {
      flex-wrap: wrap;
      align-items: flex-start;

      .search-input {
        width: 300px;
        max-width: 100%;
      }
    }
  }

}

// ============ 闲置检测 Tab 样式 ============

.zombie-analysis-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}

// 统计卡片行
.zombie-stats-row {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  width: 100%;
  margin-bottom: 12px;
}

.zombie-stat-card {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  .stat-icon-bg {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: #fff;
    flex-shrink: 0;

    &.bg-orange {
      background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
    }

    &.bg-red {
      background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
    }

    &.bg-blue {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    &.bg-green {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
  }

  .stat-content {
    flex: 1;
    min-width: 0;
  }

  .stat-value {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.2;
    color: var(--el-text-color-primary);
  }

  .stat-label {
    font-size: 11px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
    white-space: nowrap;
  }
}

// 表格区域
.zombie-table-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.zombie-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;

  .toolbar-left {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    flex: 1;
  }

  .search-input {
    width: 280px;
  }

  .filter-select {
    width: 140px;
  }
}

// 闲置检测表格样式
.zombie-table {
  .vm-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    .vm-icon {
      color: var(--el-color-primary);
      font-size: 18px;
    }

    .vm-name {
      font-weight: 500;
    }
  }

  .risk-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-weight: 500;

    .el-icon {
      font-size: 16px;
    }
  }

  .risk-icon-critical {
    color: #f56c6c;
  }

  .risk-icon-high {
    color: #e6a23c;
  }

  .risk-icon-medium {
    color: #409eff;
  }

  .risk-icon-low {
    color: #67c23a;
  }

  .days-critical {
    color: #f56c6c;
    font-weight: 600;
  }

  .days-high {
    color: #e6a23c;
    font-weight: 500;
  }

  .days-medium {
    color: #409eff;
  }

  .days-normal {
    color: var(--el-text-color-regular);
  }

  .activity-time {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  .confidence-text {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

// 空状态样式
.zombie-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  min-height: 500px;

  .empty-illustration {
    margin-bottom: 24px;
  }

  .empty-icon-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(255, 154, 86, 0.1) 0%, rgba(255, 107, 107, 0.1) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto;

    .empty-main-icon {
      font-size: 56px;
      color: #ff9a56;
    }
  }

  .empty-title {
    font-size: 22px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin: 0 0 12px 0;
  }

  .empty-desc {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0 0 32px 0;
    max-width: 400px;
    text-align: center;
  }

  .empty-features {
    list-style: none;
    padding: 0;
    margin: 0 0 32px 0;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px 32px;

    li {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--el-text-color-regular);

      .el-icon {
        color: var(--el-color-success);
        font-size: 18px;
      }
    }
  }

  .run-analysis-btn {
    min-width: 140px;
    height: 44px;
    font-size: 16px;
  }
}

@media (max-width: 1200px) {
  .zombie-stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .zombie-empty-state .empty-features {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .zombie-toolbar .search-input {
    width: 100%;
  }

  .zombie-toolbar .filter-select {
    width: calc(50% - 6px);
  }
}

@media (max-width: 800px) {
  .overview-grid .o-main {
    grid-template-columns: 1fr;
  }
}
</style>
