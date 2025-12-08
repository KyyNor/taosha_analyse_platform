"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { taskService } from "@/lib/services/fraudhunterService";
import type { TaskProgress, TaskResult } from "@/lib/services/fraudhunterService";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function TaskDetailPage() {
  const router = useRouter();
  const params = useParams();
  const taskId = params.id as string;
  const { confirm, DialogComponent } = useConfirmDialog();

  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const autoRefreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 加载任务进度
  const loadProgress = async () => {
    try {
      const progressData = await taskService.getProgress(taskId);
      setProgress(progressData);

      // 如果任务已完成，加载结果
      if (progressData.status === "success" || progressData.status === "failed") {
        try {
          const resultData = await taskService.getResult(taskId);
          setResult(resultData);
        } catch (error) {
          console.error("Failed to load task result:", error);
        }
      }
    } catch (error) {
      console.error("Failed to load task progress:", error);
      toast.error("加载任务信息失败");
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadProgress();
  }, [taskId]);

  // 自动刷新机制
  useEffect(() => {
    // 清除之前的定时器
    if (autoRefreshTimerRef.current) {
      clearInterval(autoRefreshTimerRef.current);
      autoRefreshTimerRef.current = null;
    }

    // 如果任务运行中，设置自动刷新
    if (progress && (progress.status === "pending" || progress.status === "running")) {
      autoRefreshTimerRef.current = setInterval(() => {
        loadProgress();
      }, 3000); // 每3秒刷新一次
    }

    // 组件卸载时清除定时器
    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
        autoRefreshTimerRef.current = null;
      }
    };
  }, [progress?.status]);

  // 取消任务
  const handleCancel = () => {
    confirm({
      title: "确认取消任务",
      description: `确定要取消任务 ${taskId} 吗？`,
      variant: "destructive",
      onConfirm: async () => {
        try {
          await taskService.cancel(taskId);
          await loadProgress();
        } catch (error: any) {
          console.error("取消任务失败:", error);
          toast.error(error.message || "取消任务失败");
        }
      }
    });
  };

  // 状态Badge渲染
  const renderStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      pending: "secondary",
      running: "default",
      success: "default",
      failed: "destructive",
      cancelled: "outline"
    };
    const labels: Record<string, string> = {
      pending: "待执行",
      running: "运行中",
      success: "成功",
      failed: "失败",
      cancelled: "已取消"
    };
    return <Badge variant={variants[status] || "default"}>{labels[status] || status}</Badge>;
  };

  // 格式化剩余时间
  const formatRemainingTime = (seconds: number | undefined) => {
    if (!seconds) return "计算中...";
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes > 0) {
      return `约 ${minutes} 分 ${secs} 秒`;
    }
    return `约 ${secs} 秒`;
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!progress) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">任务不存在</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push("/fraudhunter/dry-run")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <h1 className="text-2xl font-bold">任务详情</h1>
          {renderStatusBadge(progress.status)}
        </div>
        <div className="flex gap-2">
          {(progress.status === "pending" || progress.status === "running") && (
            <Button variant="destructive" onClick={handleCancel}>
              取消任务
            </Button>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">执行ID</div>
              <div className="mt-1 p-2 bg-muted rounded font-mono text-sm">
                {progress.task_id}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">任务类型</div>
              <div className="mt-1 p-2 bg-muted rounded">
                <Badge variant="outline">
                  {progress.task_type === "indicator_task" ? "指标任务" :
                   progress.task_type === "indicator" ? "指标" : progress.task_type}
                </Badge>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">开始时间</div>
              <div className="mt-1 p-2 bg-muted rounded text-sm">
                {progress.start_time
                  ? new Date(progress.start_time).toLocaleString()
                  : "未开始"}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground">结束时间</div>
              <div className="mt-1 p-2 bg-muted rounded text-sm">
                {progress.end_time
                  ? new Date(progress.end_time).toLocaleString()
                  : "未结束"}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 进度信息 */}
      {(progress.status === "pending" || progress.status === "running") && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>执行进度</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium">进度</span>
                <span className="text-sm text-muted-foreground">
                  {progress.progress !== undefined ? `${progress.progress.toFixed(1)}%` : "0%"}
                </span>
              </div>
              <Progress value={progress.progress || 0} />
            </div>

            {progress.current_step && (
              <div>
                <div className="text-sm font-medium text-muted-foreground">当前步骤</div>
                <div className="mt-1 p-2 bg-muted rounded">
                  {progress.current_step}
                </div>
              </div>
            )}

            {progress.estimated_remaining_seconds !== undefined && (
              <div>
                <div className="text-sm font-medium text-muted-foreground">预计剩余时间</div>
                <div className="mt-1 p-2 bg-muted rounded">
                  {formatRemainingTime(progress.estimated_remaining_seconds)}
                </div>
              </div>
            )}

            <p className="text-sm text-blue-600">
              ⏱️ 自动刷新已启用（每3秒）
            </p>
          </CardContent>
        </Card>
      )}

      {/* 执行结果 */}
      {result && (progress.status === "success" || progress.status === "failed") && (
        <Card>
          <CardHeader>
            <CardTitle>执行结果</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-muted-foreground">执行状态</div>
                <div className="mt-1">
                  {renderStatusBadge(result.status)}
                </div>
              </div>
              {result.duration_seconds !== undefined && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground">执行时长</div>
                  <div className="mt-1 p-2 bg-muted rounded">
                    {result.duration_seconds} 秒
                  </div>
                </div>
              )}
            </div>

            {result.result && (
              <div className="space-y-4">
                {/* 统计信息 */}
                <div className="grid grid-cols-2 gap-4">
                  {result.result.total_records !== undefined && (
                    <div>
                      <div className="text-sm font-medium text-muted-foreground">总记录数</div>
                      <div className="mt-1 p-2 bg-muted rounded font-semibold">
                        {result.result.total_records} 条
                      </div>
                    </div>
                  )}
                  {result.result.execution_time_seconds !== undefined && (
                    <div>
                      <div className="text-sm font-medium text-muted-foreground">SQL执行时间</div>
                      <div className="mt-1 p-2 bg-muted rounded font-semibold">
                        {result.result.execution_time_seconds} 秒
                      </div>
                    </div>
                  )}
                </div>

                {/* 样本数据表格 */}
                {result.result.sample_result && result.result.sample_result.length > 0 && (
                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-2">
                      样本数据（前 {result.result.sample_result.length} 条）
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
                            {result.result.sample_result.map((row: any, index: number) => (
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
      )}
      <DialogComponent />
    </div>
  );
}
