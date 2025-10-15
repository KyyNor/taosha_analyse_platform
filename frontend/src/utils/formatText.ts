/**
 * 文本格式化工具函数
 * 用于智能格式化各种文本内容，支持JSON、多行文本等
 */

/**
 * 智能格式化文本内容
 * @param text 要格式化的文本内容
 * @returns 格式化后的文本
 */
export function formatText(text: string | undefined | null): string {
  if (!text || typeof text !== 'string') {
    return text || ''
  }

  // 去除首尾空白字符
  const trimmedText = text.trim()

  // 尝试解析为JSON
  try {
    const parsed = JSON.parse(trimmedText)
    return JSON.stringify(parsed, null, 2)
  } catch {
    // 不是有效的JSON，继续其他格式化
  }

  // 检查是否包含换行符，如果包含就保持原样
  if (trimmedText.includes('\n')) {
    return trimmedText
  }

  // 检查是否是很长的单行文本，如果是且看起来像JSON但解析失败，尝试美化
  if (trimmedText.length > 100 && (trimmedText.includes('{') || trimmedText.includes('['))) {
    // 尝试修复可能损坏的JSON字符串
    try {
      // 替换单引号为双引号
      const fixedJson = trimmedText.replace(/'/g, '"')
      const parsed = JSON.parse(fixedJson)
      return JSON.stringify(parsed, null, 2)
    } catch {
      // 仍然失败，保持原样
    }
  }

  // 对于普通文本，检查是否需要处理长行
  if (trimmedText.length > 200) {
    // 尝试在逗号、冒号等位置换行
    return trimmedText
      .replace(/([.,;:])(\S)/g, '$1 $2')  // 在标点后加空格
      .replace(/([{}[\]])/g, ' $1 ')     // 在括号前后加空格
      .trim()
  }

  return trimmedText
}

/**
 * 格式化JSON内容，确保正确的缩进和换行
 * @param data 要格式化的数据
 * @returns 格式化后的JSON字符串
 */
export function formatJson(data: any): string {
  if (data === null || data === undefined) {
    return ''
  }

  try {
    if (typeof data === 'string') {
      // 如果是字符串，尝试解析为JSON后再格式化
      const parsed = JSON.parse(data)
      return JSON.stringify(parsed, null, 2)
    } else {
      // 如果是对象，直接格式化
      return JSON.stringify(data, null, 2)
    }
  } catch {
    // JSON解析失败，返回原字符串
    return typeof data === 'string' ? data : String(data)
  }
}

/**
 * 判断文本是否为JSON格式
 * @param text 要检查的文本
 * @returns 是否为有效的JSON格式
 */
export function isJson(text: string): boolean {
  if (!text || typeof text !== 'string') {
    return false
  }

  try {
    JSON.parse(text.trim())
    return true
  } catch {
    return false
  }
}

/**
 * 判断文本是否包含换行符
 * @param text 要检查的文本
 * @returns 是否包含换行符
 */
export function hasNewlines(text: string): boolean {
  return text.includes('\n')
}

/**
 * 获取文本格式的CSS类名
 * @param text 要检查的文本
 * @returns 建议的CSS类名
 */
export function getTextFormatClass(text: string): string {
  if (!text) return ''

  if (isJson(text)) {
    return 'font-mono text-xs bg-base-200 p-2 rounded-lg shadow-inner'
  }

  if (hasNewlines(text)) {
    return 'whitespace-pre-wrap text-xs bg-base-200 p-2 rounded-lg shadow-inner'
  }

  if (text.length > 100) {
    return 'whitespace-pre-wrap text-xs bg-base-200 p-2 rounded-lg shadow-inner'
  }

  return 'text-sm'
}

/**
 * 获取适合显示文本的HTML标签
 * @param text 要显示的文本
 * @param customClass 自定义CSS类名
 * @returns 格式化后的HTML内容
 */
export function getFormattedText(text: string | undefined | null, customClass = ''): string {
  const formattedText = formatText(text)
  const baseClass = getTextFormatClass(text || '')
  const finalClass = customClass ? `${baseClass} ${customClass}` : baseClass

  if (baseClass.includes('font-mono') || baseClass.includes('whitespace-pre-wrap')) {
    return `<pre class="${finalClass}">${formattedText}</pre>`
  }

  return `<div class="${finalClass}">${formattedText}</div>`
}