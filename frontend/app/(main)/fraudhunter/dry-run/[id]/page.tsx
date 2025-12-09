"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { taskService } from "@/lib/services/fraudhunterService";
import type { TaskProgress, TaskResult } from "@/lib/services/fraudhunterService";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

// 导入组件
import { TaskHeader, renderStatusBadge } from "./components/TaskHeader";
import { TaskProgressCard } from "./components/TaskProgress";

// 导入模板
import { ModelBacktestTemplate } from "./templates/ModelBacktestTemplate";
import { IndicatorTaskTemplate } from "./templates/IndicatorTaskTemplate";

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

  // 根据任务类型渲染结果模板
  const renderResultTemplate = () => {
    if (!result || !progress) return null;
    
    const taskType = progress.task_type;
    
    // 模型回测任务
    if (taskType === 'model_backtest') {
      return (
        <ModelBacktestTemplate 
          result={result.result} 
          taskId={taskId} 
        />
      );
    }
    
    // 指标任务（默认）
    return (
      <IndicatorTaskTemplate 
        result={result.result} 
        status={result.status}
      />
    );
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

  const isRunning = progress.status === "pending" || progress.status === "running";
  const isCompleted = progress.status === "success" || progress.status === "failed";

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
          {isRunning && (
            <Button variant="destructive" onClick={handleCancel}>
              取消任务
            </Button>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <TaskHeader progress={progress} />

      {/* 进度信息 - 仅在运行中显示 */}
      {isRunning && <TaskProgressCard progress={progress} />}

      {/* 执行结果 - 根据任务类型渲染不同模板 */}
      {isCompleted && result && renderResultTemplate()}

      <DialogComponent />
    </div>
  );
}
