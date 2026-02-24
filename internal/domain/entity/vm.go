// Package entity 定义领域实体
package entity

import "time"

// VM 虚拟机领域实体
type VM struct {
	id          uint
	vmKey       string
	name        string
	datacenter  string
	cpu         CPU
	memory      Memory
	powerState  PowerState
	network     NetworkInfo
	guestOS     string
	hostName    string
	collectedAt time.Time
}

// NewVM 创建 VM 实体
func NewVM(vmKey, name string, cpu CPU, memory Memory) *VM {
	return &VM{
		vmKey:      vmKey,
		name:       name,
		cpu:        cpu,
		memory:     memory,
		powerState: PowerStateUnknown,
	}
}

// GetID 获取 ID
func (v *VM) GetID() uint {
	return v.id
}

// SetID 设置 ID
func (v *VM) SetID(id uint) {
	v.id = id
}

// GetName 获取名称
func (v *VM) GetName() string {
	return v.name
}

// GetVMKey 获取 VM Key
func (v *VM) GetVMKey() string {
	return v.vmKey
}

// IsRunning 是否正在运行
func (v *VM) IsRunning() bool {
	return v.powerState == PowerStatePoweredOn
}

// GetMemoryGB 获取内存（GB）
func (v *VM) GetMemoryGB() float64 {
	return v.memory.ToGB()
}

// CPU CPU 值对象
type CPU struct {
	Count int32 // 核心数
	MHz   int32 // 频率
}

// TotalMHz 总 MHz
func (c CPU) TotalMHz() int64 {
	return int64(c.Count) * int64(c.MHz)
}

// Memory 内存值对象
type Memory struct {
	MB int32
}

// ToGB 转换为 GB
func (m Memory) ToGB() float64 {
	return float64(m.MB) / 1024
}

// PowerState 电源状态
type PowerState string

const (
	PowerStatePoweredOn  PowerState = "poweredOn"
	PowerStatePoweredOff PowerState = "poweredOff"
	PowerStateSuspended  PowerState = "suspended"
	PowerStateUnknown    PowerState = "unknown"
)

// NetworkInfo 网络信息
type NetworkInfo struct {
	IPAddress string
	MAC       string
}
