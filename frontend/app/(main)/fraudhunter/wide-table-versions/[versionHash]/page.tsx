"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Clock, XCircle, AlertCircle, PlayCircle } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell
} from "@/components/ui/table";
import { wideTableVersionService, indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { WideTableVersionDetail, WideTableVersionProgress, DateProgressDetail } from "@/lib/services/fraudhunterService";

export default function WideTableVersionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const versionHash = params.versionHash as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<WideTableVersionDetail | null>(null);
  const [progressData, setProgressData] = useState<WideTableVersionProgress | null>(null);

  // 补数相关状态
  const [rerunDialogOpen, setRerunDialogOpen] = useState(false);
  const [selectedDateProgress, setSelectedDateProgress] = useState<DateProgressDetail | null>(null);
  const [rerunStartDate, setRerunStartDate] = useState("");
  const [rerunEndDate, setRerunEndDate] = useState("");
  const [isRerunning, setIsRerunning] = useState(false);

  // 加载详情数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await wideTableVersionService.getDetail(versionHash);
      setData(result);
    } catch (error: any) {
      console.error("Failed to load version detail:", error);
      toast.error("加载版本详情失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载进度数据
  const loadProgress = async () => {
    try {
      const result = await wideTableVersionService.getProgress(versionHash);
      setProgressData(result);
    } catch (error: any) {
      console.error("Failed to load progress:", error);
      toast.error("加载执行进度失败");
    }
  };

  useEffect(() => {
    if (versionHash) {
      loadData();
      loadProgress();
    }
  }, [versionHash]);

  // 按任务分组指标
  const groupIndicatorsByTask = () => {
    if (!data?.indicators) return {};

    const grouped: Record<number, {
      task_id: number;
      task_name?: string;
      indicators: typeof data.indicators;
    }> = {};

    data.indicators.forEach(indicator => {
      const taskId = indicator.indicator_task_id || 0;
      if (!grouped[taskId]) {
        grouped[taskId] = {
          task_id: taskId,
          task_name: taskId > 0 ? `任务ID: ${taskId}` : '未分配任务',
          indicators: []
        };
      }
      grouped[taskId].indicators.push(indicator);
    });

    return grouped;
  };

  // 打开补数对话框
  const handleOpenRerunDialog = (progress: DateProgressDetail) => {
    setSelectedDateProgress(progress);
    setRerunStartDate(progress.etl_date);
    setRerunEndDate(progress.etl_date);
    setRerunDialogOpen(true);
  };

  // 执行批量补数
  const handleConfirmRerun = async () => {
    if (!selectedDateProgress || !rerunStartDate) {
      toast.warning("请选择补数日期");
      return;
    }

    if (selectedDateProgress.incomplete_tasks.length === 0) {
      toast.warning("没有需要补数的任务");
      return;
    }

    setIsRerunning(true);
    try {
      // 批量调用补数API
      const promises = selectedDateProgress.incomplete_tasks.map(task =>
        indicatorTaskService.rerun(task.task_id, {
          start_date: rerunStartDate,
          end_date: rerunEndDate || undefined,
        })
      );

      const results = await Promise.allSettled(promises);

      // 统计成功和失败数量
      const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
      const failCount = results.length - successCount;

      if (successCount > 0) {
        toast.success(`成功提交 ${successCount} 个补数任务${failCount > 0 ? `，${failCount} 个失败` : ''}`);
        setRerunDialogOpen(false);
        // 刷新进度数据
        await loadProgress();
      } else {
        toast.error("所有补数任务提交失败");
      }
    } catch (error: any) {
      console.error("Failed to rerun tasks:", error);
      toast.error(error.response?.data?.detail || "补数失败");
    } finally {
      setIsRerunning(false);
    }
  };

  // 获取状态Badge
  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      current: "default",
      target: "secondary",
      history: "outline",
      skipped: "destructive"
    };
    const labels: Record<string, string> = {
      current: "当前版本",
      target: "目标版本",
      history: "历史版本",
      skipped: "已跳过"
    };
    return <Badge variant={variants[status] || "default"}>{labels[status] || status}</Badge>;
  };

  // 获取宽表名称显示
  const getTableNameLabel = (name: string) => {
    const labels: Record<string, string> = {
      dep_acct_wide_table: "存款账户宽表",
      cust_wide_table: "客户宽表",
      loan_acct_wide_table: "贷款账户宽表"
    };
    return labels[name] || name;
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">版本不存在</div>
      </div>
    );
  }

  const groupedIndicators = groupIndicatorsByTask();

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push("/fraudhunter/wide-table-versions")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {getTableNameLabel(data.wide_table_name)}
              {getStatusBadge(data.status)}
            </h1>
            <p className="text-muted-foreground">
              版本号: <code className="bg-muted px-2 py-1 rounded">{data.version_hash}</code>
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={() => { loadData(); loadProgress(); }}>
          刷新
        </Button>
      </div>

      <div className="grid gap-6">
        {/* 卡片1: 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">宽表名称</label>
                <p className="font-medium">{getTableNameLabel(data.wide_table_name)}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">状态</label>
                <p>{getStatusBadge(data.status)}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">指标数量</label>
                <p className="font-medium">{data.indicators.length} 个</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">快照数量</label>
                <p className="font-medium">{data.snapshot_count} 个</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">创建时间</label>
                <p className="text-sm">{new Date(data.created_at).toLocaleString()}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">创建人</label>
                <p className="text-sm">{data.created_by || '-'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 卡片2: 状态变更时间线 */}
        <Card>
          <CardHeader>
            <CardTitle>状态变更</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.target_at && (
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    成为目标版本: {new Date(data.target_at).toLocaleString()}
                  </span>
                </div>
              )}
              {data.current_at && (
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm">
                    成为当前版本: {new Date(data.current_at).toLocaleString()}
                  </span>
                </div>
              )}
              {data.history_at && (
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    成为历史版本: {new Date(data.history_at).toLocaleString()}
                  </span>
                </div>
              )}
              {data.skipped_at && (
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-destructive" />
                  <span className="text-sm">
                    被跳过: {new Date(data.skipped_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 卡片3: 指标清单（按任务分组） */}
        <Card>
          <CardHeader>
            <CardTitle>指标清单</CardTitle>
            <CardDescription>
              按任务分组展示，共 {Object.keys(groupedIndicators).length} 个任务组
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" className="w-full">
              {Object.entries(groupedIndicators).map(([taskId, group]) => (
                <AccordionItem value={`task-${taskId}`} key={taskId}>
                  <AccordionTrigger>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{group.task_name}</span>
                      <Badge variant="secondary">{group.indicators.length} 个指标</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>指标ID</TableHead>
                            <TableHead>指标编码</TableHead>
                            <TableHead>指标名称</TableHead>
                            <TableHead>指标类型</TableHead>
                            <TableHead>版本号</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {group.indicators.map((indicator) => (
                            <TableRow key={indicator.indicator_id}>
                              <TableCell>{indicator.indicator_id}</TableCell>
                              <TableCell>
                                <code className="bg-muted px-2 py-1 rounded text-xs">
                                  {indicator.indicator_code}
                                </code>
                              </TableCell>
                              <TableCell>{indicator.indicator_name}</TableCell>
                              <TableCell>
                                <Badge variant="outline">
                                  {indicator.indicator_type === 'offline' ? '离线' : '实时'}
                                </Badge>
                              </TableCell>
                              <TableCell>v{indicator.indicator_version}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>

        {/* 卡片4: 执行进度（含未完成任务 + 补数） */}
        <Card>
          <CardHeader>
            <CardTitle>执行进度</CardTitle>
            <CardDescription>
              最近 {progressData?.lookback_days || 30} 天的ETL执行情况
            </CardDescription>
          </CardHeader>
          <CardContent>
            {progressData && progressData.recent_progress.length > 0 ? (
              <Accordion type="multiple" className="w-full">
                {progressData.recent_progress.map((progress) => (
                  <AccordionItem value={`date-${progress.etl_date}`} key={progress.etl_date}>
                    <AccordionTrigger>
                      <div className="flex items-center gap-3 flex-1">
                        <span className="font-medium">{progress.etl_date}</span>
                        {progress.is_complete ? (
                          <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            已完成 ({progress.completed_count}/{progress.total_count})
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-orange-600">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            进行中 ({progress.completed_count}/{progress.total_count})
                          </Badge>
                        )}
                        {!progress.is_complete && progress.incomplete_tasks.length > 0 && (
                          <Badge variant="secondary">
                            {progress.incomplete_tasks.length} 个任务未完成
                          </Badge>
                        )}
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-4">
                        {/* 进度统计 */}
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>最后完成时间: {
                            progress.last_finish_time
                              ? new Date(progress.last_finish_time).toLocaleString()
                              : '-'
                          }</span>
                        </div>

                        {/* 未完成任务列表 */}
                        {progress.incomplete_tasks.length > 0 ? (
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium">未完成任务列表</h4>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenRerunDialog(progress)}
                                className="gap-1"
                              >
                                <PlayCircle className="h-3 w-3" />
                                批量补数
                              </Button>
                            </div>
                            <div className="rounded-lg border">
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>任务ID</TableHead>
                                    <TableHead>任务编码</TableHead>
                                    <TableHead>任务名称</TableHead>
                                    <TableHead>对象类型</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {progress.incomplete_tasks.map((task) => (
                                    <TableRow key={task.task_id}>
                                      <TableCell>{task.task_id}</TableCell>
                                      <TableCell>
                                        <code className="bg-muted px-2 py-1 rounded text-xs">
                                          {task.task_code}
                                        </code>
                                      </TableCell>
                                      <TableCell>{task.task_name}</TableCell>
                                      <TableCell>
                                        <Badge variant="outline">{task.object_type}</Badge>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-4 text-sm text-muted-foreground">
                            所有任务已完成
                          </div>
                        )}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                暂无执行进度数据
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 补数对话框 */}
      <Dialog open={rerunDialogOpen} onOpenChange={setRerunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>批量补数</DialogTitle>
            <DialogDescription>
              为 {selectedDateProgress?.incomplete_tasks.length || 0} 个未完成任务执行补数操作
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="start-date">开始日期 *</Label>
              <Input
                id="start-date"
                type="date"
                value={rerunStartDate}
                onChange={(e) => setRerunStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">结束日期（可选）</Label>
              <Input
                id="end-date"
                type="date"
                value={rerunEndDate}
                onChange={(e) => setRerunEndDate(e.target.value)}
                placeholder="默认为今天"
              />
            </div>

            {selectedDateProgress && (
              <div className="bg-muted p-3 rounded-lg">
                <p className="text-sm font-medium mb-2">将补数的任务：</p>
                <div className="space-y-1 text-sm text-muted-foreground">
                  {selectedDateProgress.incomplete_tasks.map((task) => (
                    <div key={task.task_id}>
                      • {task.task_code} - {task.task_name}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRerunDialogOpen(false)}
              disabled={isRerunning}
            >
              取消
            </Button>
            <Button
              onClick={handleConfirmRerun}
              disabled={isRerunning}
            >
              {isRerunning ? "提交中..." : "确认补数"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
