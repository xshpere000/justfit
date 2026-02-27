// Package security 提供安全加密功能的单元测试
package security

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCrypto_EncryptDecrypt(t *testing.T) {
	// 创建加密服务
	crypto, err := NewCrypto("test-password-12345")
	assert.NoError(t, err)
	assert.NotNil(t, crypto)

	tests := []struct {
		name      string
		plaintext string
	}{
		{
			name:      "简单字符串",
			plaintext: "Hello, World!",
		},
		{
			name:      "中文字符串",
			plaintext: "这是一个测试",
		},
		{
			name:      "特殊字符",
			plaintext: "!@#$%^&*()_+-=",
		},
		{
			name:      "空字符串",
			plaintext: "",
		},
		{
			name:      "长字符串",
			plaintext: strings.Repeat("a", 1000),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// 加密
			ciphertext, err := crypto.EncryptString(tt.plaintext)
			if tt.plaintext == "" {
				assert.NoError(t, err)
				assert.Equal(t, "", ciphertext)
			} else {
				assert.NoError(t, err)
				assert.NotEmpty(t, ciphertext)
				assert.NotEqual(t, tt.plaintext, ciphertext) // 密文不应与明文相同
			}

			// 解密
			if tt.plaintext != "" {
				decrypted, err := crypto.DecryptString(ciphertext)
				assert.NoError(t, err)
				assert.Equal(t, tt.plaintext, decrypted)
			}
		})
	}
}

func TestCrypto_DecryptInvalidCiphertext(t *testing.T) {
	crypto, err := NewCrypto("test-password")
	assert.NoError(t, err)

	// 无效的 Base64
	_, err = crypto.DecryptString("invalid-base64!!!")
	assert.Error(t, err)

	// 格式正确但解密失败
	_, err = crypto.DecryptString("dGVzdA==") // "test" in base64
	assert.Error(t, err)
}

func TestCrypto_EmptyInput(t *testing.T) {
	crypto, err := NewCrypto("test-password")
	assert.NoError(t, err)

	// 加密空字符串
	result, err := crypto.EncryptString("")
	assert.NoError(t, err)
	assert.Equal(t, "", result)

	// 解密空字符串
	result, err = crypto.DecryptString("")
	assert.NoError(t, err)
	assert.Equal(t, "", result)
}

func TestCrypto_DifferentKeys(t *testing.T) {
	crypto1, err := NewCrypto("password1")
	assert.NoError(t, err)

	crypto2, err := NewCrypto("password2")
	assert.NoError(t, err)

	plaintext := "Secret Message"

	// 用 crypto1 加密
	ciphertext1, err := crypto1.EncryptString(plaintext)
	assert.NoError(t, err)

	// 用 crypto2 解密应该失败
	_, err = crypto2.DecryptString(ciphertext1)
	assert.Error(t, err)

	// 用 crypto1 解密应该成功
	decrypted, err := crypto1.DecryptString(ciphertext1)
	assert.NoError(t, err)
	assert.Equal(t, plaintext, decrypted)
}

func TestGetMachineID(t *testing.T) {
	id, err := GetMachineID()
	assert.NoError(t, err)
	assert.NotEmpty(t, id)
	assert.NotContains(t, id, " ") // 不应包含括号
}

func TestGenerateKey(t *testing.T) {
	key1, err := GenerateKey()
	assert.NoError(t, err)
	assert.Len(t, key1, 32) // AES-256 需要 32 字节密钥

	key2, err := GenerateKey()
	assert.NoError(t, err)
	assert.Len(t, key2, 32)

	// 两次生成的密钥应该不同
	assert.NotEqual(t, key1, key2)
}

func TestEncodeDecodeKey(t *testing.T) {
	key, err := GenerateKey()
	assert.NoError(t, err)

	// 编码
	encoded := EncodeKey(key)
	assert.NotEmpty(t, encoded)

	// 解码
	decoded, err := DecodeKey(encoded)
	assert.NoError(t, err)
	assert.Equal(t, key, decoded)
}
