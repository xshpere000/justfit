// 测试主机名称和IP获取
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

	fmt.Printf("=== 检查 %d 个数据中心的虚拟机主机信息 ===\n\n", len(datacenters))

	totalVMs := 0
	vmsWithHost := 0
	vmsWithHostIP := 0

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		vmList, err := finder.VirtualMachineList(ctx, "*")
		if err != nil {
			fmt.Printf("❌ 数据中心 %s: 获取VM列表失败: %v\n", dc.Name(), err)
			continue
		}

		fmt.Printf("=== 数据中心: %s (%d 台VM) ===\n", dc.Name(), len(vmList))

		for _, vm := range vmList {
			totalVMs++

			// 使用新的方式获取主机信息
			var vmMo mo.VirtualMachine
			err = vm.Properties(ctx, vm.Reference(), []string{"name", "summary"}, &vmMo)
			if err != nil {
				fmt.Printf("  ❌ %s: 无法获取属性 - %v\n", vm.Name(), err)
				continue
			}

			hostName := "无"
			hostIP := "无"

			// 新方式：使用 RetrieveOne 获取主机对象
			if vmMo.Summary.Runtime.Host != nil {
				var hostMo mo.HostSystem
				err = client.RetrieveOne(ctx, *vmMo.Summary.Runtime.Host, []string{"name", "summary"}, &hostMo)
				if err == nil {
					hostName = hostMo.Name
					vmsWithHost++

					// 获取主机管理IP
					if hostMo.Summary.ManagementServerIp != "" {
						hostIP = hostMo.Summary.ManagementServerIp
						vmsWithHostIP++
					}
				} else {
					fmt.Printf("  ⚠️  %s: 无法获取主机对象 - %v\n", vm.Name(), err)
				}
			}

			powerState := string(vmMo.Summary.Runtime.PowerState)
			if len(vmMo.Name) > 4 && vmMo.Name[:4] == "vCLS" {
				fmt.Printf("  🔹 [vCLS] %-30s | 状态: %-10s | 主机: %-20s | 主机IP: %s\n",
					vmMo.Name, powerState, hostName, hostIP)
			} else {
				fmt.Printf("  📦 %-30s | 状态: %-10s | 主机: %-20s | 主机IP: %s\n",
					vmMo.Name, powerState, hostName, hostIP)
			}
		}
		fmt.Println()
	}

	fmt.Printf("=== 统计结果 ===\n")
	fmt.Printf("总VM数: %d\n", totalVMs)
	fmt.Printf("有主机名的VM数: %d (%.1f%%)\n", vmsWithHost, float64(vmsWithHost)*100/float64(totalVMs))
	fmt.Printf("有主机IP的VM数: %d (%.1f%%)\n", vmsWithHostIP, float64(vmsWithHostIP)*100/float64(totalVMs))
}
