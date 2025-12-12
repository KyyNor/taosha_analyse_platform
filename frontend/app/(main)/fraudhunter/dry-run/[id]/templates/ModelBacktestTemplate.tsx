"use client";

import { useState } from "react";
import { Download, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, XCircle, SkipForward, RefreshCw, Info } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// 定义模型回测结果的数据结构
interface DailyResult {
  date: string;
  status: string;
  message: string;
  rows_matched: number;
}

// 版本降级信息
interface MismatchedIndicator {
  indicator_code: string;
  indicator_name: string;
  message: string;
}

interface VersionFallback {
  wide_table_name: string;
  etl_date: string;
  expected_version: string;
  actual_version: string;
  fallback_reason: 'indicator_not_in_current' | 'indicator_version_upgraded' | 'current_not_exist';
  mismatched_indicators: MismatchedIndicator[];
}

interface ModelBacktestResultData {
  total_days: number;
  success_days: number;
  skipped_days: number;
  failed_days: number;
  total_rows_matched: number;
  daily_results: DailyResult[];
  warnings: string[];
  matched_records: Record<string, any>[];
  log_content?: string;
  version_fallbacks?: VersionFallback[];
}

interface ModelBacktestTemplateProps {
  result: ModelBacktestResultData;
  taskId: string;
}

// Excel 导出工具函数
async function exportToExcel(taskId: string) {
  try {
    // 调用后端Excel导出接口
    const response = await api.get(`/fraudhunter/tasks/${taskId}/export/excel`, {
      responseType: 'blob'
    });

    // 创建下载链接
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });

    // 从响应头获取文件名，或使用默认文件名
    const contentDisposition = response.headers['content-disposition'];
    let filename = `backtest_${taskId}.xlsx`;

    if (contentDisposition && contentDisposition.includes('filename=')) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error: any) {
    console.error('导出Excel失败:', error);

    // 尝试解析错误信息
    let errorMessage = '导出Excel失败';
    if (error.response && error.response.data) {
      try {
        const errorText = await error.response.data.text();
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = '导出Excel失败，请稍后重试';
      }
    }

    alert(errorMessage);
  }
}

// 状态图标组件
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'skipped':
      return <SkipForward className="h-4 w-4 text-yellow-500" />;
    default:
      return null;
  }
}

// 获取降级原因的中文描述
function getFallbackReasonText(reason: string): { text: string; color: string } {
  switch (reason) {
    case 'indicator_not_in_current':
      return { text: '指标仅在target版本存在', color: 'text-blue-600' };
    case 'indicator_version_upgraded':
      return { text: '指标版本已升级', color: 'text-orange-600' };
    case 'current_not_exist':
      return { text: 'current版本不存在', color: 'text-yellow-600' };
    default:
      return { text: reason, color: 'text-gray-600' };
  }
}

// 版本降级信息卡片组件
function VersionFallbackCard({ fallbacks }: { fallbacks: VersionFallback[] }) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!fallbacks || fallbacks.length === 0) return null;

  // 按宽表分组统计
  const groupedByTable = fallbacks.reduce((acc, fb) => {
    if (!acc[fb.wide_table_name]) {
      acc[fb.wide_table_name] = [];
    }
    acc[fb.wide_table_name].push(fb);
    return acc;
  }, {} as Record<string, VersionFallback[]>);

  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-blue-100/50">
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-blue-700">
                <RefreshCw className="h-5 w-5" />
                宽表版本降级提示
                <Badge variant="secondary" className="ml-2">
                  {fallbacks.length} 次降级
                </Badge>
              </div>
              {isExpanded ? (
                <ChevronUp className="h-5 w-5 text-blue-600" />
              ) : (
                <ChevronDown className="h-5 w-5 text-blue-600" />
              )}
            </CardTitle>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-4">
            <div className="text-sm text-blue-600 flex items-start gap-2 mb-4">
              <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>
                部分日期的宽表数据因指标变更使用了target版本（正在同步中）而非current版本。
                这可能是因为指标新上线或指标版本已升级。
              </span>
            </div>
            
            {Object.entries(groupedByTable).map(([tableName, tableFallbacks]) => (
              <div key={tableName} className="border border-blue-200 rounded-lg p-4 bg-white">
                <h4 className="font-medium text-blue-800 mb-3 flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-blue-100 rounded text-sm">{tableName}</span>
                  <span className="text-sm text-muted-foreground">
                    ({tableFallbacks.length} 个日期受影响)
                  </span>
                </h4>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">日期</TableHead>
                      <TableHead className="w-[180px]">降级原因</TableHead>
                      <TableHead>影响指标</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tableFallbacks.map((fb, idx) => {
                      const reasonInfo = getFallbackReasonText(fb.fallback_reason);
                      return (
                        <TableRow key={idx}>
                          <TableCell className="font-mono">{fb.etl_date}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={reasonInfo.color}>
                              {reasonInfo.text}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {fb.mismatched_indicators && fb.mismatched_indicators.length > 0 ? (
                              <div className="space-y-1">
                                {fb.mismatched_indicators.map((ind, indIdx) => (
                                  <div key={indIdx} className="text-sm">
                                    <span className="font-medium">{ind.indicator_name}</span>
                                    <span className="text-muted-foreground ml-1">
                                      ({ind.indicator_code})
                                    </span>
                                    {ind.message && (
                                      <span className="text-muted-foreground ml-2 text-xs">
                                        - {ind.message}
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span className="text-muted-foreground text-sm">-</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ))}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export function ModelBacktestTemplate({ result, taskId }: ModelBacktestTemplateProps) {
  const [isLogOpen, setIsLogOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;

  // 分页计算
  const totalRecords = result.matched_records?.length || 0;
  const totalPages = Math.ceil(totalRecords / pageSize);
  const paginatedRecords = result.matched_records?.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  ) || [];

  // 获取表格列（从第一条记录推断）
  const columns = result.matched_records && result.matched_records.length > 0
    ? Object.keys(result.matched_records[0])
    : [];

  return (
    <div className="space-y-6">
      {/* 执行情况统计卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>执行情况</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <div className="text-2xl font-bold">{result.total_days}</div>
              <div className="text-sm text-muted-foreground">总天数</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{result.success_days}</div>
              <div className="text-sm text-green-600">成功</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{result.skipped_days}</div>
              <div className="text-sm text-yellow-600">跳过</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">{result.failed_days}</div>
              <div className="text-sm text-red-600">失败</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{result.total_rows_matched}</div>
              <div className="text-sm text-blue-600">命中记录</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 每日执行详情表格 */}
      <Card>
        <CardHeader>
          <CardTitle>每日执行详情</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">日期</TableHead>
                <TableHead className="w-[100px]">状态</TableHead>
                <TableHead>消息</TableHead>
                <TableHead className="w-[100px] text-right">命中数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.daily_results.map((day, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono">{day.date}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <StatusIcon status={day.status} />
                      <Badge variant={
                        day.status === 'success' ? 'default' :
                        day.status === 'failed' ? 'destructive' :
                        'secondary'
                      }>
                        {day.status === 'success' ? '成功' :
                         day.status === 'failed' ? '失败' :
                         day.status === 'skipped' ? '跳过' : day.status}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{day.message}</TableCell>
                  <TableCell className="text-right font-semibold">{day.rows_matched}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 版本降级信息 */}
      {result.version_fallbacks && result.version_fallbacks.length > 0 && (
        <VersionFallbackCard fallbacks={result.version_fallbacks} />
      )}

      {/* 警告信息 */}
      {result.warnings && result.warnings.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-700">
              <AlertTriangle className="h-5 w-5" />
              警告信息
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.warnings.map((warning, index) => (
                <li key={index} className="text-sm text-yellow-700 flex items-start gap-2">
                  <span className="text-yellow-500">•</span>
                  {warning}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 命中记录表格 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>命中记录 ({totalRecords} 条)</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportToExcel(taskId)}
            disabled={totalRecords === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            导出 Excel
          </Button>
        </CardHeader>
        <CardContent>
          {totalRecords > 0 ? (
            <>
              <div className="border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[60px]">#</TableHead>
                        {columns.map((col) => (
                          <TableHead key={col} className="min-w-[120px]">
                            {col}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginatedRecords.map((record, index) => (
                        <TableRow key={index}>
                          <TableCell className="text-muted-foreground">
                            {(currentPage - 1) * pageSize + index + 1}
                          </TableCell>
                          {columns.map((col) => (
                            <TableCell key={col} className="font-mono text-sm">
                              {String(record[col] ?? '')}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* 分页控件 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    显示 {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, totalRecords)} / {totalRecords} 条
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      上一页
                    </Button>
                    <span className="flex items-center px-3 text-sm">
                      {currentPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              没有命中记录
            </div>
          )}
        </CardContent>
      </Card>

      {/* 执行日志 */}
      {result.log_content && (
        <Card>
          <Collapsible open={isLogOpen} onOpenChange={setIsLogOpen}>
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer hover:bg-muted/50">
                <CardTitle className="flex items-center justify-between">
                  执行日志
                  {isLogOpen ? (
                    <ChevronUp className="h-5 w-5" />
                  ) : (
                    <ChevronDown className="h-5 w-5" />
                  )}
                </CardTitle>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent>
                <pre className="p-4 bg-muted rounded-lg text-sm font-mono whitespace-pre-wrap overflow-x-auto">
                  {result.log_content}
                </pre>
              </CardContent>
            </CollapsibleContent>
          </Collapsible>
        </Card>
      )}
    </div>
  );
}