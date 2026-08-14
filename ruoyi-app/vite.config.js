import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = dirname(fileURLToPath(import.meta.url))
const outputDir = process.env.UNI_OUTPUT_DIR || 'dist'

function copyCaptureWorklet() {
  return {
    name: 'copy-capture-worklet',
    apply: 'build',
    closeBundle() {
      // AudioWorklet is loaded through a runtime URL, so Vite cannot discover it
      // from the renderjs bundle. Copy it explicitly into both H5 and app outputs.
      const source = resolve(projectRoot, 'static/audio/pcm-capture-worklet.js')
      const target = resolve(projectRoot, outputDir, 'static/audio/pcm-capture-worklet.js')
      mkdirSync(dirname(target), { recursive: true })
      copyFileSync(source, target)
    }
  }
}

export default defineConfig({
  plugins: [uni(), copyCaptureWorklet()],
  build: {
    sourcemap: false,
    // 项目源码沿用 RuoYi uni-app 的“根目录即源码目录”结构，不能直接套用
    // DCloud CLI 默认的 src/ 目录。显式使用 UNI_OUTPUT_DIR，确保 Android
    // 本地打包资源完整写入 unpackage/dist/build/app-plus，而不是覆盖 H5 dist。
    outDir: outputDir
  }
})
