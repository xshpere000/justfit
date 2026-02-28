// 测试主机名称和IP获取 - 改进版
package main

import (
	"context"
	"fmt"
	"log"
	"net/url"

	"github.com/vmware/govmomi"
	"github.com/vmware/govmomi/find"
	"github.com/vmware/govmomi/session"
	"github.com/vmware/govmomi/vim25/mo"
)

func main() {
	host := "10.103.116.116"
	port := 443
	username := "administrator@vsphere.local"
	password := "Admin@123."
	insecure := true

	ctx := context.Background()
	u, err := url.Parse(fmt.Sprintf("https://%s:%d/sdk", host, port))
	if err != nil {
		log.Fatal(err)
	}

	client, err := govmomi.NewClient(ctx, u, insecure)
	if err != nil {
		log.Fatal(err)
	}
	defer client.Logout(ctx)

	sm := session.NewManager(client.Client)
	userInfo := url.UserPassword(username, password)
	if err := sm.Login(ctx, userInfo); err != nil {
		log.Fatal(err)
	}

	finder := find.NewFinder(client.Client, true)

	datacenters, err := finder.DatacenterList(ctx, "*")
	if err != nil || len(datacenters) == 0 {
		log.Fatal(err)
	}

	fmt.Printf("=== 检查主机信息（多种方式） ===\n\n")

	// 先获取所有主机的信息
	hostSystems := make(map[string]mo.HostSystem)
	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		hostList, err := finder.HostSystemList(ctx, "*")
		if err != nil {
			continue
		}

		for _, h := range hostList {
			var hostMo mo.HostSystem
			if err := h.Properties(ctx, h.Reference(), []string{"name", "summary", "config.network.vnic"}, &hostMo); err == nil {
				hostSystems[h.Reference().Value] = hostMo
			}
		}
	}

	fmt.Printf("找到 %d 台主机\n\n", len(hostSystems))

	// 显示主机详细信息
	fmt.Println("=== 主机列表 ===")
	for ref, hostMo := range hostSystems {
		fmt.Printf("主机: %s\n", hostMo.Name)
		fmt.Printf("  Reference: %s\n", ref)

		// 尝试多种方式获取主机IP
		ipFromManagement := "无"
		if hostMo.Summary.ManagementServerIp != "" {
			ipFromManagement = hostMo.Summary.ManagementServerIp
		}
		fmt.Printf("  ManagementServerIp: %s\n", ipFromManagement)

		// 从网络配置中获取管理网络IP
		var managementIP string
		if hostMo.Config != nil && hostMo.Config.Network != nil {
			for _, vnic := range hostMo.Config.Network.Vnic {
				// 查找管理网络的 vnic (通常是 vmk0)
				if vnic.Device == "vmk0" {
					if vnic.Spec.Ip != nil {
						managementIP = vnic.Spec.Ip.IpAddress
						break
					}
				}
			}
		}
		if managementIP != "" {
			fmt.Printf("  管理网络IP (vmk0): %s\n", managementIP)
		}

		fmt.Println()
	}

	// 检查VM的主机信息
	fmt.Println("\n=== VM与主机关联 ===")
	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		vmList, err := finder.VirtualMachineList(ctx, "*")
		if err != nil {
			continue
		}

		fmt.Printf("\n数据中心: %s\n", dc.Name())

		// 统计每个主机上的VM数量
		hostVMCount := make(map[string]int)

		for _, vm := range vmList {
			var vmMo mo.VirtualMachine
			err = vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime"}, &vmMo)
			if err != nil {
				continue
			}

			hostRef := ""
			if vmMo.Summary.Runtime.Host != nil {
				hostRef = vmMo.Summary.Runtime.Host.Value
			}

			if hostRef != "" {
				if hostMo, ok := hostSystems[hostRef]; ok {
					hostVMCount[hostMo.Name]++
				}
			}
		}

		// 显示统计
		for hostName, count := range hostVMCount {
			fmt.Printf("  主机 '%s': %d 台VM\n", hostName, count)
		}
	}
}
