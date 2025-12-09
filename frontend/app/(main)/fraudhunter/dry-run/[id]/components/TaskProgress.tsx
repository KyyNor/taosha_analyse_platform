"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { TaskProgress as TaskProgressType } from "@/lib/services/fraudhunterService";

interface TaskProgressProps {
  progress: TaskProgressType;
}

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

export function TaskProgressCard({ progress }: TaskProgressProps) {
  return (
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
  );
}