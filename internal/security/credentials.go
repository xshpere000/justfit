// Package security 提供凭据管理服务
package security

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"justfit/internal/appdir"
	"justfit/internal/storage"
)

var (
	// ErrCredentialNotFound 凭据不存在
	ErrCredentialNotFound = errors.New("credential not found")
	// ErrCredentialExists 凭据已存在
	ErrCredentialExists = errors.New("credential already exists")
)

// CredentialInfo 凭据信息（不包含敏感数据）
type CredentialInfo struct {
	ID       uint   `json:"id"`
	Name     string `json:"name"`
	Platform string `json:"platform"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Username string `json:"username"`
	Insecure bool   `json:"insecure"`
}

// EncryptedCredential 加密后的凭据
type EncryptedCredential struct {
	ID            uint   `json:"id"`
	Name          string `json:"name"`
	Platform      string `json:"platform"`
	Host          string `json:"host"`
	Port          int    `json:"port"`
	Username      string `json:"username"`
	EncryptedData string `json:"encryptedData"` // Base64 编码的加密凭据
	Insecure      bool   `json:"insecure"`
}

// CredentialManager 凭据管理器
type CredentialManager struct {
	crypto   *Crypto
	dataFile string
	mu       sync.RWMutex
}

// NewCredentialManager 创建凭据管理器
func NewCredentialManager(dataDir string) (*CredentialManager, error) {
	if dataDir == "" {
		// 使用 appdir 模块获取应用数据目录
		var err error
		dataDir, err = appdir.GetAppDataDir()
		if err != nil {
			return nil, fmt.Errorf("获取应用数据目录失败: %w", err)
		}
	}

	// 确保目录存在
	if err := os.MkdirAll(dataDir, 0700); err != nil {
		return nil, err
	}

	// 生成或获取加密密钥
	key, err := getOrCreateKey(dataDir)
	if err != nil {
		return nil, err
	}

	crypto, err := NewCryptoFromKey(key)
	if err != nil {
		return nil, err
	}

	return &CredentialManager{
		crypto:   crypto,
		dataFile: filepath.Join(dataDir, "credentials.enc"),
	}, nil
}

// getOrCreateKey 获取或创建加密密钥
func getOrCreateKey(dataDir string) ([]byte, error) {
	keyFile := filepath.Join(dataDir, ".key")

	// 尝试读取现有密钥
	if key, err := os.ReadFile(keyFile); err == nil {
		return key, nil
	}

	// 生成新密钥
	key, err := GenerateKey()
	if err != nil {
		return nil, err
	}

	// 保存密钥
	if err := os.WriteFile(keyFile, key, 0600); err != nil {
		return nil, err
	}

	return key, nil
}

// SaveConnection 保存连接凭据（加密）
func (cm *CredentialManager) SaveConnection(conn *storage.Connection) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// 加载现有凭据
	creds, err := cm.loadAll()
	if err != nil {
		return err
	}

	// 准备要加密的数据
	credData := map[string]string{
		"username": conn.Username,
		"password": conn.Password,
	}
	dataBytes, err := json.Marshal(credData)
	if err != nil {
		return err
	}

	// 加密
	encrypted, err := cm.crypto.Encrypt(dataBytes)
	if err != nil {
		return err
	}

	// 更新或添加
	cred := EncryptedCredential{
		ID:            conn.ID,
		Name:          conn.Name,
		Platform:      conn.Platform,
		Host:          conn.Host,
		Port:          conn.Port,
		Username:      conn.Username,
		EncryptedData: encrypted,
		Insecure:      conn.Insecure,
	}

	// 查找并更新
	found := false
	for i, c := range creds {
		if c.ID == conn.ID {
			creds[i] = cred
			found = true
			break
		}
	}
	if !found {
		creds = append(creds, cred)
	}

	return cm.saveAll(creds)
}

// LoadConnection 加载连接凭据（解密）
func (cm *CredentialManager) LoadConnection(conn *storage.Connection) error {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	creds, err := cm.loadAll()
	if err != nil {
		return err
	}

	for _, c := range creds {
		if c.ID == conn.ID {
			// 解密
			decrypted, err := cm.crypto.Decrypt(c.EncryptedData)
			if err != nil {
				return err
			}

			// 解析凭据数据
			var credData map[string]string
			if err := json.Unmarshal(decrypted, &credData); err != nil {
				return err
			}

			// 填充到连接对象
			conn.Username = credData["username"]
			conn.Password = credData["password"]
			return nil
		}
	}

	return ErrCredentialNotFound
}

// LoadAllCredentials 加载所有凭据信息（不包含密码）
func (cm *CredentialManager) LoadAllCredentials() ([]CredentialInfo, error) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	creds, err := cm.loadAll()
	if err != nil {
		return nil, err
	}

	result := make([]CredentialInfo, len(creds))
	for i, c := range creds {
		result[i] = CredentialInfo{
			ID:       c.ID,
			Name:     c.Name,
			Platform: c.Platform,
			Host:     c.Host,
			Port:     c.Port,
			Username: c.Username,
			Insecure: c.Insecure,
		}
	}

	return result, nil
}

// DeleteCredential 删除凭据
func (cm *CredentialManager) DeleteCredential(id uint) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	creds, err := cm.loadAll()
	if err != nil {
		return err
	}

	// 过滤掉要删除的凭据
	newCreds := make([]EncryptedCredential, 0, len(creds))
	for _, c := range creds {
		if c.ID != id {
			newCreds = append(newCreds, c)
		}
	}

	return cm.saveAll(newCreds)
}

// loadAll 加载所有加密凭据
func (cm *CredentialManager) loadAll() ([]EncryptedCredential, error) {
	if _, err := os.Stat(cm.dataFile); os.IsNotExist(err) {
		return []EncryptedCredential{}, nil
	}

	data, err := os.ReadFile(cm.dataFile)
	if err != nil {
		return nil, err
	}

	if len(data) == 0 {
		return []EncryptedCredential{}, nil
	}

	var creds []EncryptedCredential
	if err := json.Unmarshal(data, &creds); err != nil {
		return nil, err
	}

	return creds, nil
}

// saveAll 保存所有加密凭据
func (cm *CredentialManager) saveAll(creds []EncryptedCredential) error {
	data, err := json.MarshalIndent(creds, "", "  ")
	if err != nil {
		return err
	}

	// 原子写入（先写到临时文件再重命名）
	tempFile := cm.dataFile + ".tmp"
	if err := os.WriteFile(tempFile, data, 0600); err != nil {
		return err
	}

	return os.Rename(tempFile, cm.dataFile)
}
