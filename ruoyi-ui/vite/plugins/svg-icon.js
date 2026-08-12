import fs from 'node:fs'
import path from 'path'

const virtualModuleId = 'virtual:svg-icons-register'
const resolvedVirtualModuleId = `\0${virtualModuleId}`

function buildSprite(iconDir) {
  const symbols = fs.readdirSync(iconDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.svg'))
    .map((entry) => {
      const source = fs.readFileSync(path.join(iconDir, entry.name), 'utf8')
      const svgTag = source.match(/<svg\b([^>]*)>/i)?.[1] || ''
      const width = svgTag.match(/\bwidth=["']([\d.]+)(?:px)?["']/i)?.[1]
      const height = svgTag.match(/\bheight=["']([\d.]+)(?:px)?["']/i)?.[1]
      const viewBox = svgTag.match(/\bviewBox=["']([^"']+)["']/i)?.[1]
        || `0 0 ${width || 24} ${height || 24}`
      const rootFill = svgTag.match(/\bfill=["']([^"']+)["']/i)?.[1]
      const rootStroke = svgTag.match(/\bstroke=["']([^"']+)["']/i)?.[1]
      let body = source.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>\s*$/i, '')

      // 后台图标统一跟随当前文字颜色，同时保留明确声明的透明区域。
      body = body.replace(/\s(fill|stroke)=["'](?!none\b|currentColor\b|url\()[^"']+["']/gi, ' $1="currentColor"')
      const fill = !rootFill || rootFill.toLowerCase() !== 'none' ? 'currentColor' : 'none'
      const stroke = rootStroke && rootStroke.toLowerCase() !== 'none' ? 'currentColor' : null
      const rootAttrs = [`fill="${fill}"`, stroke && `stroke="${stroke}"`].filter(Boolean).join(' ')
      return `<symbol id="icon-${path.basename(entry.name, '.svg')}" viewBox="${viewBox}" ${rootAttrs}>${body}</symbol>`
    })
    .join('')
  return `<svg aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">${symbols}</svg>`
}

export default function createSvgIcon() {
  const iconDir = path.resolve(process.cwd(), 'src/assets/icons/svg')
  return {
    name: 'tmall-smart-home-svg-sprite',
    resolveId(id) {
      return id === virtualModuleId ? resolvedVirtualModuleId : null
    },
    load(id) {
      if (id !== resolvedVirtualModuleId) return null
      const sprite = JSON.stringify(buildSprite(iconDir))
      return `const sprite = ${sprite};
        if (!document.getElementById('tmall-smart-home-svg-sprite')) {
          const container = document.createElement('div');
          container.id = 'tmall-smart-home-svg-sprite';
          container.innerHTML = sprite;
          document.body.insertBefore(container, document.body.firstChild);
        }`
    }
  }
}
