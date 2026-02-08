// Package security 提供安全加密服务
package security

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"os"
	"runtime"
)

var (
	// ErrInvalidCiphertext 密文格式错误
	ErrInvalidCiphertext = errors.New("invalid ciphertext")
	// ErrInvalidKey 密钥错误
	ErrInvalidKey = errors.New("invalid key")
)

// Crypto 加密服务
type Crypto struct {
	key []byte
}

// NewCrypto 创建加密服务
func NewCrypto(password string) (*Crypto, error) {
	if password == "" {
		return nil, errors.New("password cannot be empty")
	}

	// 从密码派生密钥 (使用 SHA256)
	key := sha256.Sum256([]byte(password))

	return &Crypto{
		key: key[:],
	}, nil
}

// NewCryptoFromKey 直接从密钥创建
func NewCryptoFromKey(key []byte) (*Crypto, error) {
	if len(key) != 32 {
		return nil, ErrInvalidKey
	}

	return &Crypto{
		key: key,
	}, nil
}

// Encrypt 加密数据
func (c *Crypto) Encrypt(plaintext []byte) (string, error) {
	if len(plaintext) == 0 {
		return "", nil
	}

	block, err := aes.NewCipher(c.key)
	if err != nil {
		return "", fmt.Errorf("创建 cipher 失败: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("创建 GCM 失败: %w", err)
	}

	// 生成随机 nonce
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("生成 nonce 失败: %w", err)
	}

	// 加密
	ciphertext := gcm.Seal(nonce, nonce, plaintext, nil)

	// Base64 编码: nonce + ciphertext
	result := base64.StdEncoding.EncodeToString(ciphertext)

	return result, nil
}

// EncryptString 加密字符串
func (c *Crypto) EncryptString(plaintext string) (string, error) {
	if plaintext == "" {
		return "", nil
	}
	return c.Encrypt([]byte(plaintext))
}

// Decrypt 解密数据
func (c *Crypto) Decrypt(ciphertext string) ([]byte, error) {
	if ciphertext == "" {
		return []byte{}, nil
	}

	// Base64 解码
	data, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return nil, fmt.Errorf("base64 解码失败: %w", err)
	}

	block, err := aes.NewCipher(c.key)
	if err != nil {
		return nil, fmt.Errorf("创建 cipher 失败: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("创建 GCM 失败: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return nil, ErrInvalidCiphertext
	}

	nonce, cipherData := data[:nonceSize], data[nonceSize:]

	// 解密
	plaintext, err := gcm.Open(nil, nonce, cipherData, nil)
	if err != nil {
		return nil, fmt.Errorf("解密失败: %w", err)
	}

	return plaintext[:], nil
}

// DecryptString 解密字符串
func (c *Crypto) DecryptString(ciphertext string) (string, error) {
	plaintext, err := c.Decrypt(ciphertext)
	if err != nil {
		return "", err
	}
	return string(plaintext), nil
}

// GetMachineID 获取机器唯一标识
func GetMachineID() (string, error) {
	var id string

	switch runtime.GOOS {
	case "windows":
		// Windows: 使用机器 GUID
		id = getWindowsMachineID()
	case "darwin":
		// macOS: 使用硬件 UUID
		id = getMacMachineID()
	case "linux":
		// Linux: 使用 machine-id
		id = getLinuxMachineID()
	default:
		// 其他系统生成随机 ID
		idBytes := make([]byte, 16)
		if _, err := rand.Read(idBytes); err != nil {
			return "", err
		}
		id = fmt.Sprintf("%x", idBytes)
	}

	if id == "" {
		return "", errors.New("无法获取机器 ID")
	}

	return id, nil
}

// getWindowsMachineID 获取 Windows 机器 ID
func getWindowsMachineID() string {
	// 简化实现，实际应该读取注册表
	// HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography\MachineGuid
	// 这里返回一个基于主机名的替代方案
	hostname, _ := os.Hostname()
	return fmt.Sprintf("windows-%s", hostname)
}

// getMacMachineID 获取 macOS 机器 ID
func getMacMachineID() string {
	// 简化实现，实际应该使用 ioreg 或 system_profiler
	hostname, _ := os.Hostname()
	return fmt.Sprintf("macos-%s", hostname)
}

// getLinuxMachineID 获取 Linux 机器 ID
func getLinuxMachineID() string {
	// 尝试读取 /etc/machine-id
	if data, err := os.ReadFile("/etc/machine-id"); err == nil {
		if len(data) > 0 {
			return string(data[:32])
		}
	}
	// 回退到 dbus-id
	if data, err := os.ReadFile("/var/lib/dbus/machine-id"); err == nil {
		if len(data) > 0 {
			return string(data[:32])
		}
	}
	// 最终回退到主机名
	hostname, _ := os.Hostname()
	return fmt.Sprintf("linux-%s", hostname)
}

// GenerateKey 生成随机密钥
func GenerateKey() ([]byte, error) {
	key := make([]byte, 32) // 256 bits for AES-256
	if _, err := rand.Read(key); err != nil {
		return nil, err
	}
	return key, nil
}

// EncodeKey 编码密钥为 Base64
func EncodeKey(key []byte) string {
	return base64.StdEncoding.EncodeToString(key)
}

// DecodeKey 解码 Base64 密钥
func DecodeKey(encodedKey string) ([]byte, error) {
	return base64.StdEncoding.DecodeString(encodedKey)
}
