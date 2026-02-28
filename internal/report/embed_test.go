package report

import (
	"fmt"
	"io/fs"
	"testing"
)

// TestCheckEmbeddedFonts 检查嵌入的字体文件
func TestCheckEmbeddedFonts(t *testing.T) {
	fmt.Println("检查嵌入的字体文件...")

	fileCount := 0
	var fontFileSize int64
	var templateExists bool

	err := fs.WalkDir(assets, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			fileCount++
			info, _ := d.Info()
			fmt.Printf("  - %s (%d bytes)\n", path, info.Size())
			// 检查黑体字体文件
			if path == fontFilePath {
				fontFileSize = info.Size()
			}
			if path == "template.md" {
				templateExists = true
			}
		}
		return nil
	})

	if err != nil {
		t.Fatalf("遍历失败: %v", err)
	}

	fmt.Printf("\n总共嵌入了 %d 个文件\n", fileCount)

	if !templateExists {
		t.Error("template.md 未嵌入")
	} else {
		fmt.Println("✅ template.md 已嵌入")
	}

	if fontFileSize == 0 {
		t.Errorf("字体文件未嵌入或大小为 0 (期望: %s)", fontFilePath)
	} else {
		fmt.Printf("✅ 字体文件大小: %d bytes (%s)\n", fontFileSize, fontFilePath)
	}

	// 尝试读取字体文件
	data, err := assets.ReadFile(fontFilePath)
	if err != nil {
		t.Fatalf("读取字体文件失败: %v", err)
	}

	fmt.Printf("✅ 成功读取字体文件: %d bytes\n", len(data))

	if len(data) < 1000 {
		t.Errorf("字体文件大小异常: %d bytes (太小)", len(data))
	}

	// 检查字体文件格式（TTF 格式头部应该是 00 01 00 00）
	if len(data) >= 4 {
		header := string(data[0:4])
		if header == "ttcf" {
			t.Error("字体文件是 TTC 格式（不支持），需要 TTF 格式")
		} else {
			fmt.Printf("✅ 字体格式正确 (不是 TTC 集合格式)\n")
		}
	}

	// 尝试读取模板文件
	templateContent, err := assets.ReadFile("template.md")
	if err != nil {
		t.Fatalf("读取 template.md 失败: %v", err)
	}

	fmt.Printf("✅ 成功读取 template.md: %d bytes\n", len(templateContent))
}
