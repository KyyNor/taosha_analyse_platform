// 为了在工具文件中使用 nextTick，我们需要从 vue 导入
import { nextTick } from 'vue'
import Prism from 'prismjs'
import 'prismjs/components/prism-sql'
import 'prismjs/themes/prism.css'
import 'prismjs/themes/prism-tomorrow.css'

// 检测当前主题状态
const isDarkTheme = (): boolean => {
  return document.documentElement.getAttribute('data-theme') === 'dark' ||
         document.documentElement.classList.contains('dark') ||
         window.matchMedia('(prefers-color-scheme: dark)').matches
}

/**
 * 动态应用 Prism 主题
 */
export const applyPrismTheme = () => {
  const dark = isDarkTheme()

  // 移除现有的主题样式
  const existingLinks = document.querySelectorAll('link[data-prism-theme]')
  existingLinks.forEach(link => link.remove())

  // 创建新的主题样式
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.setAttribute('data-prism-theme', 'true')

  if (dark) {
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/themes/prism-tomorrow.min.css'
  } else {
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/themes/prism.min.css'
  }

  document.head.appendChild(link)
}

/**
 * 初始化 Prism.js 语法高亮
 */
export const initHighlight = async () => {
  await nextTick()
  applyPrismTheme()
  Prism.highlightAll()
}

/**
 * 高亮 SQL 代码
 * @param sql SQL 代码字符串
 * @returns 高亮后的 HTML 字符串
 */
export const highlightSql = (sql: string): string => {
  if (!sql) return ''
  return Prism.highlight(sql, Prism.languages.sql, 'sql')
}

// 导出 Prism 实例，供需要直接使用的场景
export { Prism }
