/**
 * 文件下载工具函数
 */

import { AxiosResponse } from 'axios';

/**
 * 从响应头中提取文件名
 * @param response Axios响应对象
 * @param defaultFilename 默认文件名（当响应头中没有文件名时使用）
 * @returns 文件名
 */
export function extractFilenameFromResponse(
  response: AxiosResponse,
  defaultFilename: string
): string {
  const contentDisposition = response.headers['content-disposition'];

  if (contentDisposition && contentDisposition.includes('filename=')) {
    // 尝试匹配 filename="xxx" 或 filename=xxx
    const filenameMatch = contentDisposition.match(/filename[*]?=["']?([^"';]+)["']?/i);
    if (filenameMatch && filenameMatch[1]) {
      // 处理 UTF-8 编码的文件名 (filename*=UTF-8''xxx)
      let filename = filenameMatch[1];
      if (filename.includes("UTF-8''")) {
        filename = decodeURIComponent(filename.split("UTF-8''")[1]);
      }
      return filename;
    }
  }

  return defaultFilename;
}

/**
 * 下载Blob文件
 * @param blob Blob对象
 * @param filename 文件名
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;

  // 触发下载
  document.body.appendChild(link);
  link.click();

  // 清理
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * 从Axios响应下载文件（优先使用响应头中的文件名）
 * @param response Axios响应对象（responseType: 'blob'）
 * @param defaultFilename 默认文件名（当响应头中没有文件名时使用）
 */
export function downloadFromResponse(
  response: AxiosResponse,
  defaultFilename: string
): void {
  // 创建Blob对象
  const blob = new Blob([response.data], {
    type: response.headers['content-type'] || 'application/octet-stream'
  });

  // 提取文件名
  const filename = extractFilenameFromResponse(response, defaultFilename);

  // 下载文件
  downloadBlob(blob, filename);
}

/**
 * 生成带时间戳的文件名
 * @param prefix 文件名前缀
 * @param extension 文件扩展名（如 'xlsx', 'csv'）
 * @returns 带时间戳的文件名
 */
export function generateTimestampedFilename(
  prefix: string,
  extension: string
): string {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
  return `${prefix}_${timestamp}.${extension}`;
}
