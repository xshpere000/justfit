// Package connector 提供云平台连接器接口定义
package connector

import (
	"context"
	"fmt"
	"time"
)

// Connector 云平台连接器接口
type Connector interface {
	// Close 关闭连接
	Close() error

	// TestConnection 测试连接是否正常
	TestConnection() error

	// GetClusters 获取集群信息
	GetClusters() ([]ClusterInfo, error)

	// GetHosts 获取主机信息
	GetHosts() ([]HostInfo, error)

	// GetVMs 获取虚拟机信息
	GetVMs() ([]VMInfo, error)

	// GetVMMetrics 获取虚拟机性能指标
	GetVMMetrics(datacenter, vmName string, startTime, endTime time.Time, cpuCount int32) (*VMMetrics, error)
}

// NewConnector 创建连接器
func NewConnector(config *ConnectionConfig) (Connector, error) {
	switch config.Platform {
	case PlatformVCenter:
		return NewVCenterClient(config)
	case PlatformH3CUIS:
		return NewUISConnector(config)
	default:
		return nil, fmt.Errorf("不支持的平台类型: %s", config.Platform)
	}
}

// ConnectorManager 连接器管理器
type ConnectorManager struct {
	connectors map[uint]Connector
}

// NewConnectorManager 新建连接器管理器
func NewConnectorManager() *ConnectorManager {
	return &ConnectorManager{
		connectors: make(map[uint]Connector),
	}
}

// Get 获取连接器
func (cm *ConnectorManager) Get(config *ConnectionConfig) (Connector, error) {
	// 检查是否已存在
	if conn, ok := cm.connectors[config.ID]; ok {
		// 测试连接是否仍然有效
		if err := conn.TestConnection(); err == nil {
			return conn, nil
		}
		// 连接失效，移除
		delete(cm.connectors, config.ID)
		conn.Close()
	}

	// 创建新连接
	conn, err := NewConnector(config)
	if err != nil {
		return nil, err
	}

	cm.connectors[config.ID] = conn
	return conn, nil
}

// RemoveByID 根据 ID 移除连接器
func (cm *ConnectorManager) RemoveByID(id uint) {
	if conn, ok := cm.connectors[id]; ok {
		conn.Close()
		delete(cm.connectors, id)
	}
}

// Remove 移除连接器
func (cm *ConnectorManager) Remove(id uint) {
	cm.RemoveByID(id)
}

// CloseAll 关闭所有连接
func (cm *ConnectorManager) CloseAll() {
	for id, conn := range cm.connectors {
		conn.Close()
		delete(cm.connectors, id)
	}
}

// WithContext 带超时的连接器获取
func (cm *ConnectorManager) WithContext(ctx context.Context, config *ConnectionConfig) (Connector, error) {
	type result struct {
		connector Connector
		err       error
	}

	ch := make(chan result, 1)

	go func() {
		connector, err := cm.Get(config)
		ch <- result{connector: connector, err: err}
	}()

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case res := <-ch:
		return res.connector, res.err
	}
}
