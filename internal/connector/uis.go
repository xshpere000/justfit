// Package connector 提供 H3C UIS 连接器实现
package connector

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/vmware/govmomi/vim25/types"
)

// UISConnector H3C UIS 连接器
type UISConnector struct {
	config *ConnectionConfig
	client *http.Client
	mu     sync.RWMutex
}

// UISVMInfo UIS 虚拟机信息
type UISVMInfo struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	UUID        string `json:"uuid,omitempty"`
	ClusterID   int    `json:"clusterId,omitempty"`
	ClusterName string `json:"clusterName,omitempty"`
	HostID      int    `json:"hostId,omitempty"`
	HostName    string `json:"hostName,omitempty"`
	PowerState  string `json:"vmStatus,omitempty"`
	GuestOS     string `json:"osDesc,omitempty"`
	IPAddress   string `json:"ipAddr,omitempty"`
	CpuCount    int    `json:"cpuCount,omitempty"`
	MemoryMB    int    `json:"memoryMB,omitempty"`
}

type UISClusterInfo struct {
	ID           int
	HostPoolID   int
	HostPoolName string
	Name         string
	EnableHA     int
	EnableLB     int
	Priority     int
}

type UISHostInfo struct {
	HostPoolID   int
	HostPoolName string
	HostID       int
	HostName     string
	HostIP       string
	HostStatus   int
	HAEnable     int
}

// UISReportType UIS 报表类型
type UISReportType string

const (
	UISReportCPU       UISReportType = "cpu"
	UISReportMemory    UISReportType = "memory"
	UISReportDiskRead  UISReportType = "disk_read"
	UISReportDiskWrite UISReportType = "disk_write"
	UISReportDiskUsage UISReportType = "disk_usage"
	UISReportDiskIO    UISReportType = "io"
	UISReportNetTotal  UISReportType = "net_total"
	UISReportNetIn     UISReportType = "net_in"
	UISReportNetOut    UISReportType = "net_out"
	UISReportNetSpIn   UISReportType = "net_sp_in"
	UISReportNetSpOut  UISReportType = "net_sp_out"
)

// UISReportConfig UIS 报表配置
type UISReportConfig struct {
	URL  string
	Type int
	Name string
}

// UIS 报表类型配置
var uisReportTypes = map[UISReportType]UISReportConfig{
	UISReportCPU:       {URL: "/uis/uis/report/cpuMemVm", Type: 0, Name: "CPU利用率"},
	UISReportMemory:    {URL: "/uis/uis/report/cpuMemVm", Type: 1, Name: "内存利用率"},
	UISReportDiskRead:  {URL: "/uis/uis/report/diskVm", Type: 0, Name: "磁盘读速率"},
	UISReportDiskWrite: {URL: "/uis/uis/report/diskVm", Type: 1, Name: "磁盘写速率"},
	UISReportDiskUsage: {URL: "/uis/uis/report/diskVm", Type: 3, Name: "磁盘利用率"},
	UISReportDiskIO:    {URL: "/uis/uis/report/ioVm", Type: 0, Name: "磁盘I/O吞吐量"},
	UISReportNetTotal:  {URL: "/uis/uis/report/netVm", Type: 0, Name: "网络总量"},
	UISReportNetIn:     {URL: "/uis/uis/report/netVm", Type: 1, Name: "网络读流量"},
	UISReportNetOut:    {URL: "/uis/uis/report/netVm", Type: 2, Name: "网络写流量"},
	UISReportNetSpIn:   {URL: "/uis/uis/report/netSpVm", Type: 0, Name: "网络读速率"},
	UISReportNetSpOut:  {URL: "/uis/uis/report/netSpVm", Type: 1, Name: "网络写速率"},
}

// NewUISConnector 创建 UIS 连接器
func NewUISConnector(config *ConnectionConfig) (*UISConnector, error) {
	// 创建 CookieJar 来管理 Session
	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, fmt.Errorf("创建 CookieJar 失败: %w", err)
	}

	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	client := &http.Client{
		Transport: tr,
		Jar:       jar,
		Timeout:   30 * time.Second,
	}

	conn := &UISConnector{
		config: config,
		client: client,
	}

	if err := conn.login(); err != nil {
		return nil, err
	}

	return conn, nil
}

// login 登录 UIS 服务器
func (c *UISConnector) login() error {
	url := fmt.Sprintf("https://%s/uis/spring_check", c.config.Host)

	// 构建查询参数
	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return fmt.Errorf("创建请求失败: %w", err)
	}

	// 添加 URL 查询参数
	q := req.URL.Query()
	q.Add("encrypt", "false")
	q.Add("loginType", "authorCenter")
	q.Add("name", c.config.Username)
	q.Add("password", c.config.Password)
	req.URL.RawQuery = q.Encode()

	// 发送请求（Cookie 会自动保存到 CookieJar）
	resp, err := c.client.Do(req)
	if err != nil {
		return fmt.Errorf("登录请求失败: %w", err)
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取响应失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return fmt.Errorf("解析登录响应失败: %w", err)
	}

	// loginFailErrorCode 为 0 表示登录成功，非 0 表示失败
	if errorCode, ok := result["loginFailErrorCode"].(float64); ok && errorCode != 0 {
		return fmt.Errorf("登录失败: %v", result["loginFailMessage"])
	}

	return nil
}

// GetVMList 获取虚拟机列表
// 使用 H3C UIS 的虚拟机概要信息批量接口: /uis/vm/list/summary
// 该接口返回的数据包含 cpu 和 memory 字段（单位为 MB）
func (c *UISConnector) GetVMList() ([]UISVMInfo, error) {
	url := fmt.Sprintf("https://%s/uis/vm/list/summary", c.config.Host)

	resp, err := c.get(url, nil)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	// H3C UIS 返回格式: {"statusType": "OK", "entity": {"data": [...], ...}}
	var result map[string]interface{}
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}

	// 检查响应状态
	if statusType, ok := result["statusType"].(string); !ok || statusType != "OK" {
		return nil, fmt.Errorf("获取虚拟机列表失败: %v", result)
	}

	// 获取 entity.data 数组
	entity, ok := result["entity"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("无效的响应数据格式: 缺少 entity")
	}

	data, ok := entity["data"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("无效的响应数据格式: 缺少 data")
	}

	vms := make([]UISVMInfo, 0, len(data))
	for _, item := range data {
		vm, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		id := toInt(vm["id"])
		name := toString(vm["name"])
		cpu := toInt(vm["cpu"])
		mem := toInt(vm["memory"])
		ipAddr := toString(vm["ipAddr"])
		if ipAddr == "" {
			ipAddr = firstIPv4FromAttributes(vm["ipv4Attributes"])
		}

		vms = append(vms, UISVMInfo{
			ID:          id,
			Name:        name,
			UUID:        toString(vm["uuid"]),
			ClusterID:   toInt(vm["clusterId"]),
			ClusterName: toString(vm["clusterName"]),
			HostID:      toInt(vm["hostId"]),
			HostName:    toString(vm["hostName"]),
			PowerState:  toString(vm["vmStatus"]),
			GuestOS:     toString(vm["osDesc"]),
			IPAddress:   ipAddr,
			CpuCount:    cpu,
			MemoryMB:    mem,
		})
	}

	return vms, nil
}

// GetClusterList 获取集群概要信息
func (c *UISConnector) GetClusterList() ([]UISClusterInfo, error) {
	url := fmt.Sprintf("https://%s/uis/cluster/clusterInfo/basic", c.config.Host)

	resp, err := c.get(url, nil)
	if err != nil {
		return nil, fmt.Errorf("获取集群概要失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("解析集群概要响应失败: %w", err)
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("无效的响应数据格式: 缺少 data")
	}

	clusters := make([]UISClusterInfo, 0, len(data))
	for _, item := range data {
		m, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		clusters = append(clusters, UISClusterInfo{
			ID:           toInt(m["id"]),
			HostPoolID:   toInt(m["hostPoolId"]),
			HostPoolName: toString(m["hostPoolName"]),
			Name:         toString(m["name"]),
			EnableHA:     toInt(m["enableHA"]),
			EnableLB:     toInt(m["enableLB"]),
			Priority:     toInt(m["priority"]),
		})
	}

	return clusters, nil
}

// GetHostList 获取主机概要信息
func (c *UISConnector) GetHostList() ([]UISHostInfo, error) {
	url := fmt.Sprintf("https://%s/uis/host/summary", c.config.Host)

	resp, err := c.get(url, nil)
	if err != nil {
		return nil, fmt.Errorf("获取主机概要失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("解析主机概要响应失败: %w", err)
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("无效的响应数据格式: 缺少 data")
	}

	hosts := make([]UISHostInfo, 0, len(data))
	for _, item := range data {
		m, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		hosts = append(hosts, UISHostInfo{
			HostPoolID:   toInt(m["hpId"]),
			HostPoolName: toString(m["hpName"]),
			HostID:       toInt(m["hostId"]),
			HostName:     toString(m["hostName"]),
			HostIP:       toString(m["hostIp"]),
			HostStatus:   toInt(m["hostStatus"]),
			HAEnable:     toInt(m["haEnable"]),
		})
	}

	return hosts, nil
}

// GetClusters 获取集群信息
func (c *UISConnector) GetClusters() ([]ClusterInfo, error) {
	clusters, err := c.GetClusterList()
	if err != nil {
		return nil, err
	}

	vms, _ := c.GetVMList()
	vmsByCluster := make(map[int]int)
	for _, vm := range vms {
		if vm.ClusterID > 0 {
			vmsByCluster[vm.ClusterID]++
		}
	}

	result := make([]ClusterInfo, 0, len(clusters))
	for _, cluster := range clusters {
		status := "green"
		if cluster.EnableHA == 0 {
			status = "yellow"
		}

		result = append(result, ClusterInfo{
			Name:        cluster.Name,
			Datacenter:  cluster.HostPoolName,
			TotalCpu:    0,
			TotalMemory: 0,
			NumHosts:    0,
			NumVMs:      vmsByCluster[cluster.ID],
			Status:      types.ManagedEntityStatus(status),
		})
	}

	return result, nil
}

// GetHosts 获取主机信息
func (c *UISConnector) GetHosts() ([]HostInfo, error) {
	hosts, err := c.GetHostList()
	if err != nil {
		return nil, err
	}

	vms, _ := c.GetVMList()
	vmsByHost := make(map[int]int)
	for _, vm := range vms {
		if vm.HostID > 0 {
			vmsByHost[vm.HostID]++
		}
	}

	result := make([]HostInfo, 0, len(hosts))
	for _, host := range hosts {
		connection := "connected"
		if host.HostStatus == 0 {
			connection = "disconnected"
		}

		result = append(result, HostInfo{
			Name:          host.HostName,
			Datacenter:    host.HostPoolName,
			IPAddress:     host.HostIP,
			CpuCores:      0,
			CpuMhz:        0,
			Memory:        0,
			NumVMs:        vmsByHost[host.HostID],
			Connection:    types.HostSystemConnectionState(connection),
			PowerState:    "poweredOn",
			OverallStatus: types.ManagedEntityStatus(connection),
		})
	}

	return result, nil
}

// GetVMs 获取虚拟机信息
func (c *UISConnector) GetVMs() ([]VMInfo, error) {
	vms, err := c.GetVMList()
	if err != nil {
		return nil, err
	}

	result := make([]VMInfo, len(vms))
	for i, vm := range vms {
		powerState := mapUISPowerState(vm.PowerState)
		overallStatus := "green"
		if powerState != "poweredOn" {
			overallStatus = "gray"
		}

		result[i] = VMInfo{
			Name:          vm.Name,
			Datacenter:    vm.ClusterName,
			CpuCount:      int32(vm.CpuCount),
			MemoryMB:      int32(vm.MemoryMB),
			PowerState:    types.VirtualMachinePowerState(powerState),
			IPAddress:     vm.IPAddress,
			GuestOS:       vm.GuestOS,
			HostName:      vm.HostName,
			OverallStatus: types.ManagedEntityStatus(overallStatus),
			UUID:          vm.UUID,
		}
	}

	return result, nil
}

// GetVMMetrics 获取虚拟机性能指标
func (c *UISConnector) GetVMMetrics(datacenter, vmName, vmUUID string, startTime, endTime time.Time, cpuCount int32) (*VMMetrics, error) {
	vms, err := c.GetVMList()
	if err != nil {
		return nil, err
	}

	var vmID int
	var vmCpuCount int
	var vmMemoryMB int
	for _, vm := range vms {
		if strings.TrimSpace(vmUUID) != "" && strings.EqualFold(strings.TrimSpace(vm.UUID), strings.TrimSpace(vmUUID)) {
			vmID = vm.ID
			vmCpuCount = vm.CpuCount
			vmMemoryMB = vm.MemoryMB
			break
		}

		if strings.TrimSpace(vmUUID) == "" && vm.Name == vmName {
			vmID = vm.ID
			vmCpuCount = vm.CpuCount
			vmMemoryMB = vm.MemoryMB
			break
		}
	}

	if vmID == 0 {
		return nil, fmt.Errorf("未找到虚拟机: %s", vmName)
	}

	startStr := startTime.Format("2006-01-02 15")
	endStr := endTime.Format("2006-01-02 15")
	cycle := 1

	metrics := &VMMetrics{
		VMName:    vmName,
		CPU:       []MetricSample{},
		Memory:    []MetricSample{},
		DiskRead:  []MetricSample{},
		DiskWrite: []MetricSample{},
		NetRx:     []MetricSample{},
		NetTx:     []MetricSample{},
	}
	metricErrs := make([]string, 0)

	// 获取 CPU 数据
	cpuData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportCPU)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("cpu: %v", err))
	}
	cpuSamples := parseMetricSamples(cpuData)
	// 转换百分比为绝对值 (Core)
	if vmCpuCount > 0 {
		for i := range cpuSamples {
			cpuSamples[i].Value = (cpuSamples[i].Value / 100.0) * float64(vmCpuCount)
		}
	}
	metrics.CPU = cpuSamples

	// 获取内存数据
	memData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportMemory)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("memory: %v", err))
	}
	memSamples := parseMetricSamples(memData)
	// 转换百分比为绝对值 (MB)
	if vmMemoryMB > 0 {
		for i := range memSamples {
			memSamples[i].Value = (memSamples[i].Value / 100.0) * float64(vmMemoryMB)
		}
	}
	metrics.Memory = memSamples

	// 获取磁盘读数据
	diskReadData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportDiskRead)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("disk_read: %v", err))
	}
	metrics.DiskRead = parseMetricSamples(diskReadData)

	// 获取磁盘写数据
	diskWriteData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportDiskWrite)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("disk_write: %v", err))
	}
	metrics.DiskWrite = parseMetricSamples(diskWriteData)

	// 获取网络入流量
	netRxData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportNetIn)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("net_in: %v", err))
	}
	metrics.NetRx = parseMetricSamples(netRxData)

	// 获取网络出流量
	netTxData, err := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportNetOut)
	if err != nil {
		metricErrs = append(metricErrs, fmt.Sprintf("net_out: %v", err))
	}
	metrics.NetTx = parseMetricSamples(netTxData)

	if len(metricErrs) > 0 && len(metrics.CPU) == 0 && len(metrics.Memory) == 0 && len(metrics.DiskRead) == 0 && len(metrics.DiskWrite) == 0 && len(metrics.NetRx) == 0 && len(metrics.NetTx) == 0 {
		return nil, fmt.Errorf("采集虚拟机指标失败: %s", strings.Join(metricErrs, "; "))
	}

	return metrics, nil
}

// parseMetricSamples 解析指标数据样本
func parseMetricSamples(data []interface{}) []MetricSample {
	samples := make([]MetricSample, 0)

	for _, item := range data {
		point, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		if listVal, ok := point["list"].([]interface{}); ok {
			for _, raw := range listVal {
				entry, ok := raw.(map[string]interface{})
				if !ok {
					continue
				}

				ts := parseMetricTime(toString(entry["name"]))
				val := toFloat(entry["rate"])
				if !ts.IsZero() {
					samples = append(samples, MetricSample{Timestamp: ts, Value: val})
				}
			}
			continue
		}

		var timestamp time.Time
		var value float64

		if t, ok := point["timestamp"].(string); ok {
			timestamp, _ = time.Parse("2006-01-02 15:04:05", t)
		} else if t, ok := point["time"].(string); ok {
			timestamp, _ = time.Parse("2006-01-02 15:04:05", t)
		}

		if v, ok := point["value"].(float64); ok {
			value = v
		} else if v, ok := point["value"].(string); ok {
			value, _ = strconv.ParseFloat(v, 64)
		}

		if !timestamp.IsZero() {
			samples = append(samples, MetricSample{
				Timestamp: timestamp,
				Value:     value,
			})
		}
	}

	return samples
}

func toInt(v interface{}) int {
	switch val := v.(type) {
	case float64:
		return int(val)
	case int:
		return val
	case int32:
		return int(val)
	case int64:
		return int(val)
	case string:
		i, _ := strconv.Atoi(val)
		return i
	default:
		return 0
	}
}

func toString(v interface{}) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func toFloat(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case float32:
		return float64(val)
	case int:
		return float64(val)
	case int64:
		return float64(val)
	case string:
		f, _ := strconv.ParseFloat(val, 64)
		return f
	default:
		return 0
	}
}

func firstIPv4FromAttributes(v interface{}) string {
	attrs, ok := v.([]interface{})
	if !ok {
		return ""
	}

	for _, attr := range attrs {
		m, ok := attr.(map[string]interface{})
		if !ok {
			continue
		}

		ipv4s, ok := m["ipv4s"].([]interface{})
		if !ok {
			continue
		}

		for _, ip := range ipv4s {
			ipm, ok := ip.(map[string]interface{})
			if !ok {
				continue
			}
			addr := toString(ipm["ipAddress"])
			if addr != "" {
				return addr
			}
		}
	}

	return ""
}

func mapUISPowerState(vmStatus string) string {
	status := strings.ToLower(vmStatus)
	switch status {
	case "running", "poweron", "poweredon", "started":
		return "poweredOn"
	case "shutoff", "poweroff", "poweredoff", "stopped":
		return "poweredOff"
	case "suspended", "pause", "paused":
		return "suspended"
	default:
		return "poweredOff"
	}
}

func parseMetricTime(raw string) time.Time {
	if raw == "" {
		return time.Time{}
	}

	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02 15",
		"2006-01-02",
		"2006-01",
		"2006",
	}

	for _, layout := range formats {
		if ts, err := time.Parse(layout, raw); err == nil {
			return ts
		}
	}

	return time.Time{}
}

// GetVMReport 获取虚拟机报表数据
func (c *UISConnector) GetVMReport(vmID int, startTime, endTime string, cycle int, reportType UISReportType) ([]interface{}, error) {
	config, ok := uisReportTypes[reportType]
	if !ok {
		return nil, fmt.Errorf("不支持的报表类型: %s", reportType)
	}

	params := map[string]interface{}{
		"domainId":  vmID,
		"cycle":     cycle,
		"startTime": startTime,
		"endTime":   endTime,
		"type":      config.Type,
	}

	url := fmt.Sprintf("https://%s%s", c.config.Host, config.URL)

	resp, err := c.get(url, params)
	if err != nil {
		return nil, fmt.Errorf("获取报表数据失败: %w", err)
	}

	var result interface{}
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("解析报表数据失败: %w", err)
	}

	switch v := result.(type) {
	case []interface{}:
		return v, nil
	case map[string]interface{}:
		if v["success"] == true {
			if data, ok := v["data"].([]interface{}); ok {
				return data, nil
			}
		}
		return nil, fmt.Errorf("获取报表数据失败")
	default:
		return nil, fmt.Errorf("无效的响应格式")
	}
}

// TestConnection 测试连接
func (c *UISConnector) TestConnection() error {
	_, err := c.GetVMList()
	return err
}

// Close 关闭连接
func (c *UISConnector) Close() error {
	c.client.CloseIdleConnections()
	return nil
}

// get 发送 GET 请求
func (c *UISConnector) get(url string, params map[string]interface{}) ([]byte, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	if len(params) > 0 {
		q := req.URL.Query()
		for k, v := range params {
			q.Add(k, fmt.Sprintf("%v", v))
		}
		req.URL.RawQuery = q.Encode()
	}

	return c.doRequest(req)
}

// post 发送 POST 请求
func (c *UISConnector) post(url string, body map[string]interface{}) ([]byte, error) {
	jsonData, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", url, strings.NewReader(string(jsonData)))
	if err != nil {
		return nil, err
	}

	return c.doRequest(req)
}

// doRequest 执行 HTTP 请求
func (c *UISConnector) doRequest(req *http.Request) ([]byte, error) {
	// Cookie 会自动从 CookieJar 中添加到请求
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP 请求失败: %s - %s", resp.Status, string(data))
	}

	return data, nil
}
