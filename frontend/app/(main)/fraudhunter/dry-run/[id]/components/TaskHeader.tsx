"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TaskProgress } from "@/lib/services/fraudhunterService";

interface TaskHeaderProps {
  progress: TaskProgress;
}

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

// 任务类型标签
const getTaskTypeLabel = (taskType: string) => {
  const labels: Record<string, string> = {
    indicator_task: "指标任务",
    indicator: "指标",
    model_backtest: "模型回测"
  };
  return labels[taskType] || taskType;
};

export function TaskHeader({ progress }: TaskHeaderProps) {
  return (
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
                {getTaskTypeLabel(progress.task_type)}
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
  );
}

export { renderStatusBadge };