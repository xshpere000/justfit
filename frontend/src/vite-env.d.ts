/// <reference types="vite/client" />

declare module '*.vue' {
    import type {DefineComponent} from 'vue'
    const component: DefineComponent<{}, {}, any>
    export default component
}

// SCSS 变量类型声明
declare module '*scss' {
    export const variables: any
    export const spacing: any
    export const color: any
}

interface ElectronAPI {
    minimize: () => Promise<void>
    toggleMaximize: () => Promise<void>
    close: () => Promise<void>
    isMaximized: () => Promise<boolean>
    windowMinimize: () => Promise<void>
    windowMaximize: () => Promise<void>
    windowClose: () => Promise<void>
    windowIsMaximized: () => Promise<boolean>
    getVersion: () => Promise<string>
    getDataPath: () => Promise<string>
    getBackendUrl: () => Promise<string>
    getBackendStatus: () => Promise<unknown>
    restartBackend: () => Promise<{ success: boolean }>
    stopBackend: () => Promise<{ success: boolean }>
    startBackend: () => Promise<{ success: boolean }>
}

interface Window {
    electronAPI?: ElectronAPI
}

// Wails 运行时
declare const Wails: any
