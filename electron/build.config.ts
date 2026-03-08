/**
 * Electron Build Configuration
 * Platform-specific build settings
 */

const config = {
  // Windows 配置
  windows: {
    target: 'nsis',  // Nullsoft Scriptable Install System
    icon: 'resources/icons/app.png',

    // 安装程序配置
    installerIcon: 'resources/icons/app.png',
    uninstallDisplayName: 'JustFit',
    createDesktopShortcut: true,
    createStartMenuShortcut: true,

    // 输出文件名
    artifactName: '${productName}-${version}-${arch}.${ext}',
  },

  // 资源配置
  extraResources: [
    {
      from: 'backend/',
      to: 'backend/',
      filter: ['**/*', '!**/__pycache__/**', '!**/*.pyc', '!**/.pytest_cache/**'],
    },
    {
      from: 'resources/',
      to: 'resources/',
    },
  ],

  // 文件包含
  files: [
    'electron/dist/**/*',
    'frontend/dist/**/*',
  ],

  // 输出目录
  outputDirectory: 'dist/electron',

  // 应用元数据
  appId: 'com.justfit.app',
  productName: 'JustFit',
  copyright: 'Copyright © 2025 JustFit Team',
};

export default config;
