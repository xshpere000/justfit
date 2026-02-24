// Package config 提供应用配置管理功能
// 从 .env 文件加载配置，支持多环境配置切换
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"sync"

	"github.com/joho/godotenv"
)

// Env 环境类型
type Env string

const (
	EnvDevelopment Env = "development"
	EnvTest        Env = "test"
	EnvProduction  Env = "production"
)

// Config 应用配置
type Config struct {
	// 应用配置
	AppEnv      Env
	ServerHost  string
	ServerPort  int
	DBPath      string
	LogLevel    string

	// 虚拟化平台配置
	DefaultPlatform string

	// vCenter配置
	VCENTERHost     string
	VCENTERPort     int
	VCENTERUsername string
	VCENTERPassword string
	VCENTERInsecure bool

	// H3C UIS配置
	UISHost     string
	UISPort     int
	UISUsername string
	UISPassword string
	UISInsecure bool

	// 功能开关
	EnableCollection  bool
	EnableAnalysis    bool
	AnalysisTimeout   int
	MetricsInterval   int
}

var (
	cfg  *Config
	once sync.Once
)

// Load 加载配置（单例模式）
func Load() (*Config, error) {
	var loadErr error
	once.Do(func() {
		cfg = &Config{}
		loadErr = loadConfig()
	})
	return cfg, loadErr
}

// loadConfig 从环境变量加载配置
func loadConfig() error {
	// 加载 .env 文件
	// 注意：在生产环境中可以使用环境变量覆盖
	_ = godotenv.Load()

	// 应用配置
	cfg.AppEnv = Env(getEnv("APP_ENV", string(EnvTest)))
	cfg.ServerHost = getEnv("SERVER_HOST", "0.0.0.0")
	cfg.ServerPort = getEnvInt("SERVER_PORT", 8080)
	cfg.DBPath = getEnv("DB_PATH", "./data/justfit.db")
	cfg.LogLevel = getEnv("LOG_LEVEL", "debug")

	// 虚拟化平台配置
	cfg.DefaultPlatform = getEnv("DEFAULT_PLATFORM", "h3c-uis")

	// vCenter配置
	cfg.VCENTERHost = getEnv("VCENTER_HOST", "")
	cfg.VCENTERPort = getEnvInt("VCENTER_PORT", 443)
	cfg.VCENTERUsername = getEnv("VCENTER_USERNAME", "")
	cfg.VCENTERPassword = getEnv("VCENTER_PASSWORD", "")
	cfg.VCENTERInsecure = getEnvBool("VCENTER_INSECURE", true)

	// H3C UIS配置
	cfg.UISHost = getEnv("UIS_HOST", "")
	cfg.UISPort = getEnvInt("UIS_PORT", 443)
	cfg.UISUsername = getEnv("UIS_USERNAME", "")
	cfg.UISPassword = getEnv("UIS_PASSWORD", "")
	cfg.UISInsecure = getEnvBool("UIS_INSECURE", true)

	// 功能开关
	cfg.EnableCollection = getEnvBool("ENABLE_COLLECTION", true)
	cfg.EnableAnalysis = getEnvBool("ENABLE_ANALYSIS", true)
	cfg.AnalysisTimeout = getEnvInt("ANALYSIS_TIMEOUT", 300)
	cfg.MetricsInterval = getEnvInt("METRICS_INTERVAL", 60)

	return nil
}

// Get 获取配置实例
func Get() *Config {
	if cfg == nil {
		var err error
		cfg, err = Load()
		if err != nil {
			panic(fmt.Sprintf("failed to load config: %v", err))
		}
	}
	return cfg
}

// getEnv 获取环境变量字符串值
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvInt 获取环境变量整数值
func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

// getEnvBool 获取环境变量布尔值
func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		lower := strings.ToLower(value)
		if lower == "true" || lower == "1" || lower == "yes" || lower == "on" {
			return true
		}
		if lower == "false" || lower == "0" || lower == "no" || lower == "off" {
			return false
		}
	}
	return defaultValue
}

// IsTest 检查是否为测试环境
func (c *Config) IsTest() bool {
	return c.AppEnv == EnvTest
}

// IsDevelopment 检查是否为开发环境
func (c *Config) IsDevelopment() bool {
	return c.AppEnv == EnvDevelopment
}

// IsProduction 检查是否为生产环境
func (c *Config) IsProduction() bool {
	return c.AppEnv == EnvProduction
}

// GetPlatformConfig 获取指定平台的配置
func (c *Config) GetPlatformConfig(platform string) map[string]interface{} {
	config := make(map[string]interface{})
	
	switch platform {
	case "vcenter":
		config["host"] = c.VCENTERHost
		config["port"] = c.VCENTERPort
		config["username"] = c.VCENTERUsername
		config["password"] = c.VCENTERPassword
		config["insecure"] = c.VCENTERInsecure
	case "h3c-uis", "uis":
		config["host"] = c.UISHost
		config["port"] = c.UISPort
		config["username"] = c.UISUsername
		config["password"] = c.UISPassword
		config["insecure"] = c.UISInsecure
	}
	
	return config
}

// GetDefaultPlatform 获取默认平台
func (c *Config) GetDefaultPlatform() string {
	return c.DefaultPlatform
}
