/// <reference types="vite/client" />

declare module '*.vue' {
    import type {DefineComponent} from 'vue'
    const component: DefineComponent<{}, {}, any>
    export default component
}

// SCSS 变量类型声明
declare namespace '*scss' {
    export const var: any
    export const spacing: any
    export const color: any
}

// Wails 运行时
declare const Wails: any
