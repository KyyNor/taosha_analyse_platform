/**
 * 格式化工具函数
 */

/**
 * 格式化日期时间为 yyyy-MM-dd HH:mm:ss
 */
export function formatDateTime(dateString: string | Date | null | undefined): string {
  if (!dateString) return '-';

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '-';

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    return String(dateString);
  }
}

/**
 * 格式化对象显示为JSON字符串
 */
export function formatObject(obj: any, maxLength: number = 100): string {
  if (obj === null || obj === undefined) return '-';

  if (typeof obj === 'object') {
    try {
      const jsonStr = JSON.stringify(obj, null, 2);
      return jsonStr.length > maxLength ? jsonStr.substring(0, maxLength) + '...' : jsonStr;
    } catch (error) {
      return String(obj);
    }
  }

  return String(obj);
}

/**
 * 格式化对象显示为单行JSON
 */
export function formatObjectInline(obj: any, maxLength: number = 200): string {
  if (obj === null || obj === undefined) return '-';

  if (typeof obj === 'object') {
    try {
      const jsonStr = JSON.stringify(obj);
      return jsonStr.length > maxLength ? jsonStr.substring(0, maxLength) + '...' : jsonStr;
    } catch (error) {
      return String(obj);
    }
  }

  return String(obj);
}

/**
 * 截断文本
 */
export function truncateText(text: string | null | undefined, maxLength: number = 50): string {
  if (!text) return '-';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * 格式化布尔值
 */
export function formatBoolean(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return value ? '是' : '否';
}

/**
 * 格式化数字
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return String(value);
}

/**
 * 安全地转换为字符串
 */
export function safeString(value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'string') return value;
  if (typeof value === 'object') return formatObjectInline(value);
  return String(value);
}

/**
 * 获取文件大小的可读格式
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '-';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}