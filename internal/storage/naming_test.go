package storage

import (
	"fmt"
	"os"
	"testing"
)

// TestCamelCaseNaming 测试驼峰命名是否正常工作
func TestCamelCaseNaming(t *testing.T) {
	tmpDir := "/tmp/justfit_naming_test_" + fmt.Sprintf("%d", os.Getpid())
	os.RemoveAll(tmpDir)
	os.MkdirAll(tmpDir, 0755)
	defer os.RemoveAll(tmpDir)

	// 确保删除旧数据库
	dbPath := tmpDir + "/justfit.db"
	os.Remove(dbPath)

	err := Init(&Config{DataDir: tmpDir})
	if err != nil {
		t.Fatalf("Init failed: %v", err)
	}
	defer Close()

	fmt.Println("Database initialized at:", dbPath)

	// 检查表是否正确创建
	var tableList []string
	DB.Raw("SELECT name FROM sqlite_master WHERE type='table'").Scan(&tableList)
	fmt.Println("Tables:", tableList)

	// 检查实际表名和结构
	fmt.Println("\n=== Database Schema Debug ===")

	// 列出所有表
	rows, _ := DB.Raw("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").Rows()
	defer rows.Close()

	fmt.Println("\nAll tables with CREATE SQL:")
	for rows.Next() {
		var name, sql string
		rows.Scan(&name, &sql)
		fmt.Printf("\nTable: %s\n", name)
		fmt.Printf("SQL: %s\n", sql)
	}

	// 检查 connections 表结构
	fmt.Println("\n=== Connection Table Columns ===")
	cols, _ := DB.Raw("PRAGMA table_info(connections)").Rows()
	defer cols.Close()

	hasColumns := false
	for cols.Next() {
		hasColumns = true
		var cid, notnull, pk int
		var name, ctype string
		cols.Scan(&cid, &name, &ctype, &notnull, nil, &pk)
		fmt.Printf("  %s (%s) NOT NULL=%d PK=%d\n", name, ctype, notnull, pk)
	}

	if !hasColumns {
		fmt.Println("  NO COLUMNS FOUND - TABLE STRUCTURE ISSUE!")
	}

	// 测试创建连接
	conn := &Connection{
		Name:     "test-conn",
		Platform: "vcenter",
		Host:     "192.168.1.1",
		Port:     443,
		Username: "admin",
		Password: "secret",
		Insecure: true,
	}

	fmt.Println("\n=== Creating Connection ===")
	if err := DB.Create(conn).Error; err != nil {
		t.Fatalf("Create connection failed: %v\nSQL: %s", err, DB.Statement.SQL.String())
	}

	// 测试查询连接
	var result Connection
	if err := DB.First(&result, conn.ID).Error; err != nil {
		t.Fatalf("Query connection failed: %v", err)
	}

	if result.Name != "test-conn" {
		t.Errorf("Expected name 'test-conn', got '%s'", result.Name)
	}

	fmt.Println("✓ Connection create/query works")

	// 测试创建任务
	task := &AssessmentTask{
		Name:           "测试任务",
		ConnectionID:   conn.ID,
		ConnectionName: "test-conn",
		Platform:       "vcenter",
		SelectedVMs:    "[]",
		MetricsDays:    30,
		Status:         "pending",
		Progress:       0,
	}

	if err := DB.Create(task).Error; err != nil {
		t.Fatalf("Create task failed: %v", err)
	}

	// 测试查询任务
	var taskResult AssessmentTask
	if err := DB.First(&taskResult, task.ID).Error; err != nil {
		t.Fatalf("Query task failed: %v", err)
	}

	if taskResult.Name != "测试任务" {
		t.Errorf("Expected name '测试任务', got '%s'", taskResult.Name)
	}

	if taskResult.ConnectionID != conn.ID {
		t.Errorf("Expected ConnectionID %d, got %d", conn.ID, taskResult.ConnectionID)
	}

	fmt.Println("✓ Task create/query works")

	// 检查表结构
	var columns []struct {
		Name string
		Type string
	}

	DB.Raw("PRAGMA table_info(tasks)").Scan(&columns)

	fmt.Println("\n✓ Tasks table columns:")
	for _, c := range columns {
		fmt.Printf("  - %s (%s)\n", c.Name, c.Type)
	}
}
