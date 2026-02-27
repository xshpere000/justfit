// 列出所有虚拟机及其状态
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
	finder.SetDatacenter(datacenters[0])

	vmList, err := finder.VirtualMachineList(ctx, "*")
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("=== 所有虚拟机列表 (共 %d 台) ===\n\n", len(vmList))

	poweredOnCount := 0
	poweredOffCount := 0
	unknownCount := 0

	for _, vm := range vmList {
		var vmMo mo.VirtualMachine
		if err := vm.Properties(ctx, vm.Reference(), []string{"name", "summary.runtime.powerState"}, &vmMo); err != nil {
			fmt.Printf("❌ %s: 无法获取状态\n", vm.Reference().Value)
			continue
		}

		powerState := string(vmMo.Summary.Runtime.PowerState)
		switch powerState {
		case "poweredOn":
			poweredOnCount++
		case "poweredOff":
			poweredOffCount++
		default:
			unknownCount++
		}

		if len(vmMo.Name) > 4 && vmMo.Name[:4] == "vCLS" {
			fmt.Printf("🔹 [vCLS] %s: %s\n", vmMo.Name, powerState)
		} else {
			fmt.Printf("  📦 %s: %s\n", vmMo.Name, powerState)
		}
	}

	fmt.Printf("\n=== 统计 ===\n")
	fmt.Printf("开机状态: %d\n", poweredOnCount)
	fmt.Printf("关机状态: %d\n", poweredOffCount)
	fmt.Printf("其他状态: %d\n", unknownCount)
}
