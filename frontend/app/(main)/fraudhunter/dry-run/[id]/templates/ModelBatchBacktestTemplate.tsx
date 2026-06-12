"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, ExternalLink, AlertTriangle, FileText } from "lucide-react";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { downloadFromResponse, generateTimestampedFilename } from "@/lib/utils/downloadUtils";

interface HitModel {
  model_id: number;
  model_code: string;
  model_name: string;
  child_task_id?: number;
  child_execution_id?: string;
}

interface AccountHitSummary {
  account: string;
  hit_model_count: number;
  hit_models: HitModel[];
  hit_dates: string[];
  is_whitelist: boolean;
}

interface ModelSummary {
  model_id: number;
  model_code: string;
  model_name: string;
  status: string;
  child_task_id?: number;
  child_execution_id?: string;
  total_rows_matched: number;
  hit_accounts: number;
  total_days: number;
  success_days: number;
  failed_days: number;
  skipped_days: number;
  error_message?: string;
}

interface DailySummary {
  date: string;
  success_models: number;
  failed_models: number;
  skipped_models: number;
  hit_records: number;
  hit_accounts: number;
}

interface FailedModelDetail {
  model_id: number;
  model_code: string;
  model_name: string;
  status: string;
  message: string;
  child_task_id?: number;
  child_execution_id?: string;
}

interface ModelBatchBacktestResultData {
  start_date: string;
  end_date: string;
  model_count: number;
  success_models: number;
  failed_models: number;
  cancelled_models?: number;
  total_hit_accounts: number;
  total_hit_records: number;
  model_summaries: ModelSummary[];
  account_hit_summaries: AccountHitSummary[];
  daily_summaries: DailySummary[];
  warnings: string[];
  failed_models_detail: FailedModelDetail[];
  log_content?: string;
}

interface ModelBatchBacktestTemplateProps {
  result: ModelBatchBacktestResultData;
  taskId: number;
}

const statusLabel: Record<string, string> = {
  pending: "待执行",
  running: "运行中",
  success: "成功",
  failed: "失败",
  cancelled: "已取消",
};

function statusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "success") return "default";
  if (status === "failed") return "destructive";
  if (status === "cancelled") return "outline";
  return "secondary";
}

async function exportToExcel(taskId: number) {
  const response = await api.get(`/fraudhunter/tasks/${taskId}/export/excel`, {
    responseType: "blob",
  });
  const defaultFilename = generateTimestampedFilename(`batch_backtest_${taskId}`, "xlsx");
  downloadFromResponse(response, defaultFilename);
}

export function ModelBatchBacktestTemplate({ result, taskId }: ModelBatchBacktestTemplateProps) {
  const router = useRouter();
  const [isLogOpen, setIsLogOpen] = useState(false);
  const [accountPage, setAccountPage] = useState(1);
  const pageSize = 50;

  const accountRows = result.account_hit_summaries || [];
  const totalAccountPages = Math.ceil(accountRows.length / pageSize);
  const paginatedAccounts = useMemo(() => {
    return accountRows.slice((accountPage - 1) * pageSize, accountPage * pageSize);
  }, [accountRows, accountPage]);

  const openChildTask = (childTaskId?: number) => {
    if (childTaskId) {
      router.push(`/fraudhunter/dry-run/${childTaskId}`);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>批量回测概览</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportToExcel(taskId)}
          >
            <Download className="h-4 w-4 mr-2" />
            导出 Excel
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center p-4 bg-muted rounded-lg">
              <div className="text-2xl font-bold">{result.model_count}</div>
              <div className="text-sm text-muted-foreground">模型数</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{result.success_models}</div>
              <div className="text-sm text-green-600">成功模型</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">{result.failed_models}</div>
              <div className="text-sm text-red-600">失败模型</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{result.total_hit_accounts}</div>
              <div className="text-sm text-blue-600">命中账号</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{result.total_hit_records}</div>
              <div className="text-sm text-purple-600">命中记录</div>
            </div>
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            日期范围：{result.start_date} 至 {result.end_date}
          </div>
        </CardContent>
      </Card>

      {((result.failed_models_detail?.length || 0) > 0 || (result.warnings?.length || 0) > 0) && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-700">
              <AlertTriangle className="h-5 w-5" />
              失败与警告
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {result.failed_models_detail?.map((item, index) => (
              <div key={`failed-${index}`} className="rounded border border-yellow-200 bg-white p-3">
                <div className="font-medium">{item.model_code} {item.model_name}</div>
                <div className="text-muted-foreground mt-1">{item.message}</div>
              </div>
            ))}
            {result.warnings?.map((warning, index) => (
              <div key={`warning-${index}`} className="text-yellow-800">{warning}</div>
            ))}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="accounts">
        <TabsList>
          <TabsTrigger value="accounts">账号命中汇总</TabsTrigger>
          <TabsTrigger value="models">模型执行汇总</TabsTrigger>
          <TabsTrigger value="daily">每日汇总</TabsTrigger>
        </TabsList>

        <TabsContent value="accounts" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>账号命中汇总 ({accountRows.length} 个账号)</CardTitle>
            </CardHeader>
            <CardContent>
              {accountRows.length > 0 ? (
                <>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[180px]">账号</TableHead>
                          <TableHead className="w-[120px] text-right">命中模型数</TableHead>
                          <TableHead>命中模型</TableHead>
                          <TableHead>命中日期</TableHead>
                          <TableHead className="w-[100px]">白名单</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {paginatedAccounts.map((item) => (
                          <TableRow key={item.account}>
                            <TableCell className="font-mono">{item.account}</TableCell>
                            <TableCell className="text-right font-semibold">{item.hit_model_count}</TableCell>
                            <TableCell>
                              <div className="flex flex-wrap gap-1">
                                {item.hit_models.map((model) => (
                                  <Button
                                    key={`${item.account}-${model.model_id}`}
                                    variant="outline"
                                    size="sm"
                                    className="h-7"
                                    onClick={() => openChildTask(model.child_task_id)}
                                  >
                                    {model.model_code}
                                    <ExternalLink className="h-3 w-3 ml-1" />
                                  </Button>
                                ))}
                              </div>
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {item.hit_dates.join(", ") || "-"}
                            </TableCell>
                            <TableCell>
                              <Badge variant={item.is_whitelist ? "secondary" : "outline"}>
                                {item.is_whitelist ? "是" : "否"}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {totalAccountPages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                      <div className="text-sm text-muted-foreground">
                        显示 {(accountPage - 1) * pageSize + 1} - {Math.min(accountPage * pageSize, accountRows.length)} / {accountRows.length} 个账号
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setAccountPage((page) => Math.max(1, page - 1))}
                          disabled={accountPage === 1}
                        >
                          上一页
                        </Button>
                        <span className="flex items-center px-3 text-sm">
                          {accountPage} / {totalAccountPages}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setAccountPage((page) => Math.min(totalAccountPages, page + 1))}
                          disabled={accountPage === totalAccountPages}
                        >
                          下一页
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">没有命中账号</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="models" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>模型执行汇总</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>模型</TableHead>
                      <TableHead className="w-[100px]">状态</TableHead>
                      <TableHead className="text-right">命中账号</TableHead>
                      <TableHead className="text-right">命中记录</TableHead>
                      <TableHead className="text-right">成功天数</TableHead>
                      <TableHead className="text-right">失败天数</TableHead>
                      <TableHead className="text-right">跳过天数</TableHead>
                      <TableHead className="w-[120px]">明细</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.model_summaries?.map((item) => (
                      <TableRow key={item.model_id}>
                        <TableCell>
                          <div className="font-medium">{item.model_name}</div>
                          <div className="font-mono text-xs text-muted-foreground">{item.model_code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariant(item.status)}>
                            {statusLabel[item.status] || item.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{item.hit_accounts}</TableCell>
                        <TableCell className="text-right">{item.total_rows_matched}</TableCell>
                        <TableCell className="text-right">{item.success_days}</TableCell>
                        <TableCell className="text-right">{item.failed_days}</TableCell>
                        <TableCell className="text-right">{item.skipped_days}</TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openChildTask(item.child_task_id)}
                            disabled={!item.child_task_id}
                          >
                            查看
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="daily" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>每日汇总</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead className="text-right">成功模型</TableHead>
                      <TableHead className="text-right">失败模型</TableHead>
                      <TableHead className="text-right">跳过模型</TableHead>
                      <TableHead className="text-right">命中账号</TableHead>
                      <TableHead className="text-right">命中记录</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.daily_summaries?.map((item) => (
                      <TableRow key={item.date}>
                        <TableCell className="font-mono">{item.date}</TableCell>
                        <TableCell className="text-right">{item.success_models}</TableCell>
                        <TableCell className="text-right">{item.failed_models}</TableCell>
                        <TableCell className="text-right">{item.skipped_models}</TableCell>
                        <TableCell className="text-right">{item.hit_accounts}</TableCell>
                        <TableCell className="text-right">{item.hit_records}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {result.log_content && (
        <Card>
          <Collapsible open={isLogOpen} onOpenChange={setIsLogOpen}>
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer hover:bg-muted/50">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  执行日志
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
