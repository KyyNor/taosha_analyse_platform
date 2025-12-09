"use client";

import { useState } from "react";
import { Download, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, XCircle, SkipForward } from "lucide-react";
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
}

interface ModelBacktestTemplateProps {
  result: ModelBacktestResultData;
  taskId: string;
}

// CSV 导出工具函数
function exportToCSV(data: Record<string, any>[], filename: string) {
  if (!data || data.length === 0) {
    alert("没有数据可导出");
    return;
  }

  const headers = Object.keys(data[0]);
  const csvRows = [];
  
  // 添加表头
  csvRows.push(headers.join(','));
  
  // 添加数据行
  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header];
      // 处理包含逗号或引号的值
      if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value ?? '';
    });
    csvRows.push(values.join(','));
  }
  
  const csvContent = csvRows.join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
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
            onClick={() => exportToCSV(result.matched_records, `backtest_${taskId}.csv`)}
            disabled={totalRecords === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            导出 CSV
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