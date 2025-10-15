/**
 * 时间和耗时计算工具函数
 */

/**
 * 计算两个时间点之间的耗时（毫秒）
 * @param startTime 开始时间字符串
 * @param endTime 结束时间字符串
 * @returns 耗时（毫秒），如果无法计算则返回null
 */
export function calculateDuration(startTime: string | undefined | null, endTime: string | undefined | null): number | null {
  if (!startTime || !endTime) return null

  try {
    const start = new Date(startTime).getTime()
    const end = new Date(endTime).getTime()

    if (isNaN(start) || isNaN(end)) return null

    return end - start
  } catch (error) {
    console.warn('计算耗时失败:', error)
    return null
  }
}

/**
 * 从QueryTask对象计算耗时
 * @param record 查询任务记录
 * @returns 耗时（毫秒），如果无法计算则返回null
 */
export function calculateTaskDuration(record: { created_at?: string | null; completed_at?: string | null }): number | null {
  if (!record.created_at) return null
  return calculateDuration(record.created_at, record.completed_at)
}

/**
 * 格式化耗时显示
 * @param duration 耗时（毫秒）
 * @param showEmpty 是否显示空值占位符，默认为'-'
 * @returns 格式化的耗时字符串
 */
export function formatDuration(duration: number | null | undefined, showEmpty = '-'): string {
  if (duration === null || duration === undefined || duration < 0) return showEmpty

  if (duration < 1000) {
    return `${duration}ms`
  } else if (duration < 60000) {
    return `${(duration / 1000).toFixed(2)}s`
  } else {
    const minutes = Math.floor(duration / 60000)
    const seconds = (duration % 60000) / 1000
    return `${minutes}m ${seconds.toFixed(1)}s`
  }
}

/**
 * 格式化时间显示
 * @param timeStr 时间字符串
 * @returns 格式化的时间字符串
 */
export function formatTime(timeStr: string | undefined | null): string {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 格式化日期时间显示（简化版）
 * @param timeStr 时间字符串
 * @returns 格式化的时间字符串
 */
export function formatDateTime(timeStr: string | undefined | null): string {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString()
}