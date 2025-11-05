/**
 * Markdown 渲染工具
 * 支持代码高亮和常用 Markdown 语法
 */
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 配置 marked
marked.setOptions({
  highlight: function (code: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.warn('代码高亮失败:', err)
      }
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true, // 支持换行
  gfm: true, // 启用 GitHub 风格的 Markdown
})

/**
 * 渲染 Markdown 内容
 * @param content - Markdown 文本内容
 * @returns 渲染后的 HTML 字符串
 */
export function renderMarkdown(content: string): string {
  if (!content) return ''

  try {
    return marked.parse(content)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return content
  }
}

/**
 * 检测内容是否包含 Markdown 语法
 * @param content - 文本内容
 * @returns 是否包含 Markdown 语法
 */
export function containsMarkdown(content: string): boolean {
  if (!content) return false

  const markdownPatterns = [
    /^#{1,6}\s+/m,        // 标题
    /\*\*.*?\*\*/,        // 粗体
    /\*.*?\*/,            // 斜体
    /\[.*?\]\(.*?\)/,     // 链接
    /```[\s\S]*?```/,     // 代码块
    /`.*?`/,              // 行内代码
    /^\s*[-*+]\s+/m,      // 无序列表
    /^\s*\d+\.\s+/m,      // 有序列表
    /^\s*\|.*\|/m,        // 表格
    /^\s*>\s+/m,          // 引用
  ]

  return markdownPatterns.some(pattern => pattern.test(content))
}

/**
 * 智能渲染内容（自动检测是否为 Markdown）
 * @param content - 文本内容
 * @returns 渲染后的内容（纯文本或 HTML）
 */
export function smartRender(content: string): { html: string, isMarkdown: boolean } {
  const isMarkdown = containsMarkdown(content)

  if (isMarkdown) {
    return {
      html: renderMarkdown(content),
      isMarkdown: true
    }
  } else {
    return {
      html: escapeHtml(content),
      isMarkdown: false
    }
  }
}

/**
 * HTML 转义
 * @param text - 原始文本
 * @returns 转义后的文本
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}