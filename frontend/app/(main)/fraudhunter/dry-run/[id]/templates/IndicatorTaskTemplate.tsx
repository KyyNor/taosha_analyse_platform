"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { renderStatusBadge } from "../components/TaskHeader";

interface SampleRow {
  account_id: string;
  indicator_code: string;
  indicator_value: any;
  dt: string;
}

interface IndicatorTaskResultData {
  total_records?: number;
  execution_time_seconds?: number;
  sample_result?: SampleRow[];
}

interface IndicatorTaskTemplateProps {
  result: IndicatorTaskResultData;
  status: string;
}

export function IndicatorTaskTemplate({ result, status }: IndicatorTaskTemplateProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>执行结果</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm font-medium text-muted-foreground">执行状态</div>
            <div className="mt-1">
              {renderStatusBadge(status)}
            </div>
          </div>
          {result.execution_time_seconds !== undefined && (
            <div>
              <div className="text-sm font-medium text-muted-foreground">执行时长</div>
              <div className="mt-1 p-2 bg-muted rounded">
                {result.execution_time_seconds} 秒
              </div>
            </div>
          )}
        </div>

        {result && (
          <div className="space-y-4">
            {/* 统计信息 */}
            <div className="grid grid-cols-2 gap-4">
              {result.total_records !== undefined && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">总记录数</div>
                  <div className="mt-1 p-2 bg-muted rounded font-semibold">
                    {result.total_records} 条
                  </div>
                </div>
              )}
              {result.execution_time_seconds !== undefined && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">SQL执行时间</div>
                  <div className="mt-1 p-2 bg-muted rounded font-semibold">
                    {result.execution_time_seconds} 秒
                  </div>
                </div>
              )}
            </div>

            {/* 样本数据表格 */}
            {result.sample_result && result.sample_result.length > 0 && (
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-2">
                  样本数据（前 {result.sample_result.length} 条）
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted">
                        <tr>
                          <th className="px-4 py-2 text-left text-sm font-medium">序号</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">账户ID</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">指标编码</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">指标值</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">日期</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {result.sample_result.map((row: SampleRow, index: number) => (
                          <tr key={index} className="hover:bg-muted/50">
                            <td className="px-4 py-2 text-sm">{index + 1}</td>
                            <td className="px-4 py-2 text-sm font-mono">{row.account_id}</td>
                            <td className="px-4 py-2 text-sm">
                              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                                {row.indicator_code}
                              </code>
                            </td>
                            <td className="px-4 py-2 text-sm font-semibold">{row.indicator_value}</td>
                            <td className="px-4 py-2 text-sm">{row.dt}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}