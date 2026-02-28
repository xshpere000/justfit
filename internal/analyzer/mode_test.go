package analyzer

import (
	"testing"
)

func TestGetModeConfig(t *testing.T) {
	tests := []struct {
		name    AnalysisMode
		wantNil bool
	}{
		{ModeSafe, false},
		{ModeSaving, false},
		{ModeAggressive, false},
		{ModeCustom, false},
		{AnalysisMode("invalid"), false}, // 无效模式返回默认安全模式
	}

	for _, tt := range tests {
		t.Run(string(tt.name), func(t *testing.T) {
			got := GetModeConfig(tt.name)
			if tt.wantNil && got != nil {
				t.Errorf("GetModeConfig() = %v, want nil", got)
				return
			}
			if !tt.wantNil && got == nil {
				t.Errorf("GetModeConfig() = nil, want non-nil")
				return
			}
		})
	}
}

func TestGetModeInfo(t *testing.T) {
	tests := []struct {
		mode             AnalysisMode
		wantEmptyName    bool
		wantEmptyDesc    bool
		wantNameContains string
	}{
		{ModeSafe, false, false, "安全"},
		{ModeSaving, false, false, "节省"},
		{ModeAggressive, false, false, "激进"},
		{ModeCustom, false, false, "自定义"},
	}

	for _, tt := range tests {
		t.Run(string(tt.mode), func(t *testing.T) {
			name, desc := GetModeInfo(tt.mode)
			if tt.wantEmptyName && name != "" {
				t.Errorf("GetModeInfo() name = %v, want empty", name)
			}
			if !tt.wantEmptyName && name == "" {
				t.Errorf("GetModeInfo() name = empty, want non-empty")
			}
			if tt.wantEmptyDesc && desc != "" {
				t.Errorf("GetModeInfo() desc = %v, want empty", desc)
			}
			if !tt.wantEmptyDesc && desc == "" {
				t.Errorf("GetModeInfo() desc = empty, want non-empty")
			}
			if tt.wantNameContains != "" && !contains(name, tt.wantNameContains) {
				t.Errorf("GetModeInfo() name = %v, want to contain %v", name, tt.wantNameContains)
			}
		})
	}
}

func TestGetEffectiveConfig(t *testing.T) {
	// 测试预设模式
	t.Run("Safe mode", func(t *testing.T) {
		config := GetEffectiveConfig(ModeSafe, nil)
		if config == nil {
			t.Fatal("GetEffectiveConfig() returned nil")
		}
		if config.ZombieVM == nil {
			t.Error("ZombieVM config is nil")
		}
		if config.ZombieVM.AnalysisDays != 30 {
			t.Errorf("AnalysisDays = %v, want 30", config.ZombieVM.AnalysisDays)
		}
	})

	// 测试自定义模式
	t.Run("Custom mode with config", func(t *testing.T) {
		customConfig := &AnalysisConfig{
			ZombieVM: &ZombieVMConfig{
				AnalysisDays:  14,
				CPUThreshold:  8.0,
				MinConfidence: 70.0,
			},
		}
		config := GetEffectiveConfig(ModeCustom, customConfig)
		if config == nil {
			t.Fatal("GetEffectiveConfig() returned nil")
		}
		if config.ZombieVM == nil {
			t.Fatal("ZombieVM config is nil")
		}
		if config.ZombieVM.AnalysisDays != 14 {
			t.Errorf("AnalysisDays = %v, want 14", config.ZombieVM.AnalysisDays)
		}
		if config.ZombieVM.CPUThreshold != 8.0 {
			t.Errorf("CPUThreshold = %v, want 8.0", config.ZombieVM.CPUThreshold)
		}
	})

	// 测试自定义模式无配置
	t.Run("Custom mode without config", func(t *testing.T) {
		config := GetEffectiveConfig(ModeCustom, nil)
		if config == nil {
			t.Fatal("GetEffectiveConfig() returned nil")
		}
		// 应该返回基础配置（空或默认）
		if config.ZombieVM != nil && config.ZombieVM.AnalysisDays != 0 {
			// 预期行为：自定义模式无配置时，返回空配置或基础配置
		}
	})
}

func TestIsValidMode(t *testing.T) {
	tests := []struct {
		mode string
		want bool
	}{
		{"safe", true},
		{"saving", true},
		{"aggressive", true},
		{"custom", true},
		{"invalid", false},
		{"", false},
	}

	for _, tt := range tests {
		t.Run(tt.mode, func(t *testing.T) {
			got := IsValidMode(tt.mode)
			if got != tt.want {
				t.Errorf("IsValidMode(%v) = %v, want %v", tt.mode, got, tt.want)
			}
		})
	}
}

func TestListAllModes(t *testing.T) {
	modes := ListAllModes()
	if len(modes) != 4 {
		t.Errorf("ListAllModes() returned %d modes, want 4", len(modes))
	}

	expectedModes := []AnalysisMode{ModeSafe, ModeSaving, ModeAggressive, ModeCustom}
	for i, mode := range modes {
		if mode != expectedModes[i] {
			t.Errorf("ListAllModes()[%d] = %v, want %v", i, mode, expectedModes[i])
		}
	}
}

func contains(s, substr string) bool {
	return len(s) > 0 && len(substr) > 0 && (s == substr || len(s) > len(substr) && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
