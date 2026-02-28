// 测试主机名称和IP获取 - 使用修改后的逻辑
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

	fmt.Printf("=== 使用修改后的逻辑检查VM主机信息 ===\n\n")

	totalVMs := 0
	vmsWithHostName := 0
	vmsWithHostIP := 0

	for _, dc := range datacenters {
		finder.SetDatacenter(dc)

		vmList, err := finder.VirtualMachineList(ctx, "*")
		if err != nil {
			continue
		}

		fmt.Printf("=== 数据中心: %s ===\n", dc.Name())

		for _, vm := range vmList {
			totalVMs++

			var vmMo mo.VirtualMachine
			err = vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime"}, &vmMo)
			if err != nil {
				continue
			}

			hostName := "无"
			hostIP := "无"

			// 使用修改后的逻辑：获取主机的 name, summary, config.network.vnic
			if vmMo.Summary.Runtime.Host != nil {
				var hostMo mo.HostSystem
				err = client.RetrieveOne(ctx, *vmMo.Summary.Runtime.Host, []string{"name", "summary", "config.network.vnic"}, &hostMo)
				if err == nil {
					hostName = hostMo.Name
					vmsWithHostName++

					// 从管理网络接口获取IP（通常是 vmk0）
					if hostMo.Config != nil && hostMo.Config.Network != nil {
						for _, vnic := range hostMo.Config.Network.Vnic {
							if vnic.Device == "vmk0" {
								if vnic.Spec.Ip != nil {
									hostIP = vnic.Spec.Ip.IpAddress
									vmsWithHostIP++
									break
								}
							}
						}
					}
					// 如果管理网络接口没找到IP，尝试使用 ManagementServerIp
					if hostIP == "无" && hostMo.Summary.ManagementServerIp != "" {
						hostIP = hostMo.Summary.ManagementServerIp
						vmsWithHostIP++
					}
				}
			}

			powerState := string(vmMo.Summary.Runtime.PowerState)
			fmt.Printf("  %-35s | %-10s | 主机名: %-20s | 主机IP: %s\n",
				vmMo.Name, powerState, hostName, hostIP)
		}
		fmt.Println()
	}

	fmt.Printf("=== 统计结果 ===\n")
	fmt.Printf("总VM数: %d\n", totalVMs)
	fmt.Printf("有主机名的VM数: %d (%.1f%%)\n", vmsWithHostName, float64(vmsWithHostName)*100/float64(totalVMs))
	fmt.Printf("有主机IP的VM数: %d (%.1f%%)\n", vmsWithHostIP, float64(vmsWithHostIP)*100/float64(totalVMs))
}
