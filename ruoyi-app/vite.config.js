import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig({
  plugins: [uni()],
  build: {
    sourcemap: false,
    // 项目源码沿用 RuoYi uni-app 的“根目录即源码目录”结构，不能直接套用
    // DCloud CLI 默认的 src/ 目录。显式使用 UNI_OUTPUT_DIR，确保 Android
    // 本地打包资源完整写入 unpackage/dist/build/app-plus，而不是覆盖 H5 dist。
    outDir: process.env.UNI_OUTPUT_DIR || 'dist'
  }
})
