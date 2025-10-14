import Prism from 'prismjs'
import 'prismjs/components/prism-sql'
import 'prismjs/themes/prism.css'

/**
 * 初始化 Prism.js 语法高亮
 */
export const initHighlight = async () => {
  await nextTick()
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

// 为了在工具文件中使用 nextTick，我们需要从 vue 导入
import { nextTick } from 'vue'