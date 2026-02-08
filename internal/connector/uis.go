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
)

// UISConnector H3C UIS 连接器
type UISConnector struct {
	config *ConnectionConfig
	client *http.Client
	mu     sync.RWMutex
}

// UISVMInfo UIS 虚拟机信息
type UISVMInfo struct {
	ID       int    `json:"id"`
	Name     string `json:"name"`
	CpuCount int    `json:"cpuCount,omitempty"`
	MemoryMB int    `json:"memoryMB,omitempty"`
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
func (c *UISConnector) GetVMList() ([]UISVMInfo, error) {
	params := map[string]interface{}{
		"offset": 0,
		"limit":  1000,
	}

	url := fmt.Sprintf("https://%s/uis/uis/btnSeries/resourceDetail", c.config.Host)

	resp, err := c.get(url, params)
	if err != nil {
		return nil, fmt.Errorf("获取虚拟机列表失败: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}

	if result["success"] == false {
		return nil, fmt.Errorf("获取虚拟机列表失败: %v", result["failureMessage"])
	}

	data, ok := result["data"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("无效的响应数据格式")
	}

	vms := make([]UISVMInfo, len(data))
	for i, item := range data {
		vm, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		cpu := 0
		if v, ok := vm["vcpus"].(float64); ok {
			cpu = int(v)
		} else if v, ok := vm["cpu"].(float64); ok {
			cpu = int(v)
		}

		mem := 0
		if v, ok := vm["memory"].(float64); ok {
			mem = int(v)
		} else if v, ok := vm["memSize"].(float64); ok {
			mem = int(v)
		} else if v, ok := vm["memorySize"].(float64); ok {
			mem = int(v)
		}

		vms[i] = UISVMInfo{
			ID:       int(vm["id"].(float64)),
			Name:     vm["name"].(string),
			CpuCount: cpu,
			MemoryMB: mem,
		}
	}

	return vms, nil
}

// GetClusters 获取集群信息 (UIS 没有集群概念)
func (c *UISConnector) GetClusters() ([]ClusterInfo, error) {
	return []ClusterInfo{
		{
			Name:        "H3C UIS 平台",
			Datacenter:  "default",
			TotalCpu:    0,
			TotalMemory: 0,
			NumHosts:    0,
			NumVMs:      0,
		},
	}, nil
}

// GetHosts 获取主机信息 (UIS 没有主机概念)
func (c *UISConnector) GetHosts() ([]HostInfo, error) {
	vms, err := c.GetVMList()
	if err != nil {
		return nil, err
	}

	hosts := make([]HostInfo, len(vms))
	for i, vm := range vms {
		hosts[i] = HostInfo{
			Name:       vm.Name,
			IPAddress:  "",
			CpuCores:   0,
			Memory:     0,
			NumVMs:     1,
			PowerState: "poweredOn",
		}
	}

	return hosts, nil
}

// GetVMs 获取虚拟机信息
func (c *UISConnector) GetVMs() ([]VMInfo, error) {
	vms, err := c.GetVMList()
	if err != nil {
		return nil, err
	}

	result := make([]VMInfo, len(vms))
	for i, vm := range vms {
		result[i] = VMInfo{
			Name:       vm.Name,
			PowerState: "poweredOn",
			CpuCount:   int32(vm.CpuCount),
			MemoryMB:   int32(vm.MemoryMB),
		}
	}

	return result, nil
}

// GetVMMetrics 获取虚拟机性能指标
func (c *UISConnector) GetVMMetrics(datacenter, vmName string, startTime, endTime time.Time, cpuCount int32) (*VMMetrics, error) {
	vms, err := c.GetVMList()
	if err != nil {
		return nil, err
	}

	var vmID int
	var vmCpuCount int
	var vmMemoryMB int
	for _, vm := range vms {
		if vm.Name == vmName {
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

	// 获取 CPU 数据
	cpuData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportCPU)
	cpuSamples := parseMetricSamples(cpuData)
	// 转换百分比为绝对值 (Core)
	if vmCpuCount > 0 {
		for i := range cpuSamples {
			cpuSamples[i].Value = (cpuSamples[i].Value / 100.0) * float64(vmCpuCount)
		}
	}
	metrics.CPU = cpuSamples

	// 获取内存数据
	memData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportMemory)
	memSamples := parseMetricSamples(memData)
	// 转换百分比为绝对值 (MB)
	if vmMemoryMB > 0 {
		for i := range memSamples {
			memSamples[i].Value = (memSamples[i].Value / 100.0) * float64(vmMemoryMB)
		}
	}
	metrics.Memory = memSamples

	// 获取磁盘读数据
	diskReadData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportDiskRead)
	metrics.DiskRead = parseMetricSamples(diskReadData)

	// 获取磁盘写数据
	diskWriteData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportDiskWrite)
	metrics.DiskWrite = parseMetricSamples(diskWriteData)

	// 获取网络入流量
	netRxData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportNetIn)
	metrics.NetRx = parseMetricSamples(netRxData)

	// 获取网络出流量
	netTxData, _ := c.GetVMReport(vmID, startStr, endStr, cycle, UISReportNetOut)
	metrics.NetTx = parseMetricSamples(netTxData)

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
