"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { taskService } from "@/lib/services/fraudhunterService";
import type { TaskExecution } from "@/lib/services/fraudhunterService";

export default function TasksPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<TaskExecution[]>([]);
  const autoRefreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 筛选状态
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [taskIdFilter, setTaskIdFilter] = useState<string>("");

  // 加载任务列表
  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (taskTypeFilter !== "all") params.task_type = taskTypeFilter;
      if (statusFilter !== "all") params.status = statusFilter;
      if (taskIdFilter.trim()) params.task_id = Number(taskIdFilter);

      const response = await taskService.list(params);
      setData(response.items || []);
    } catch (error) {
      console.error("Failed to load tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  // 检查是否有运行中的任务
  const hasRunningTasks = () => {
    return data.some(
      (task) => task.status === "pending" || task.status === "running"
    );
  };

  // 初始加载
  useEffect(() => {
    load();
  }, [taskTypeFilter, statusFilter, taskIdFilter]);

  // 自动刷新机制
  useEffect(() => {
    // 清除之前的定时器
    if (autoRefreshTimerRef.current) {
      clearInterval(autoRefreshTimerRef.current);
      autoRefreshTimerRef.current = null;
    }

    // 如果有运行中的任务，设置自动刷新
    if (hasRunningTasks()) {
      autoRefreshTimerRef.current = setInterval(() => {
        load();
      }, 5000); // 每5秒刷新一次
    }

    // 组件卸载时清除定时器
    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
        autoRefreshTimerRef.current = null;
      }
    };
  }, [data]);

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "execution_id", label: "执行ID", type: "text" as const },
    {
      key: "task_type",
      label: "任务类型",
      type: "text" as const,
      render: (value: string) => (
        <Badge variant="outline">
          {value === "indicator_group" ? "指标组" : value === "indicator" ? "指标" : value}
        </Badge>
      )
    },
    { key: "task_id", label: "关联ID", type: "number" as const },
    {
      key: "status",
      label: "状态",
      type: "text" as const,
      render: (value: string) => {
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
        return <Badge variant={variants[value] || "default"}>{labels[value] || value}</Badge>;
      }
    },
    { key: "start_time", label: "开始时间", type: "datetime" as const },
    { key: "end_time", label: "结束时间", type: "datetime" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const }
  ];

  // 操作处理
  const handleView = (item: TaskExecution) => {
    router.push(`/fraudhunter/tasks/${item.execution_id}`);
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">任务管理</h1>
        <p className="text-muted-foreground">监控指标和模型的执行任务</p>
        {hasRunningTasks() && (
          <p className="text-sm text-blue-600 mt-2">
            ⏱️ 检测到运行中的任务，自动刷新已启用（每5秒）
          </p>
        )}
      </div>

      {/* 筛选器 */}
      <div className="flex gap-4 mb-4">
        <Select value={taskTypeFilter} onValueChange={setTaskTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="任务类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="indicator_group">指标组</SelectItem>
            <SelectItem value="indicator">指标</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="pending">待执行</SelectItem>
            <SelectItem value="running">运行中</SelectItem>
            <SelectItem value="success">成功</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>

        <Input
          placeholder="按关联ID筛选..."
          value={taskIdFilter}
          onChange={(e) => setTaskIdFilter(e.target.value)}
          className="w-[200px]"
          type="number"
        />
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onView={handleView}
        searchPlaceholder="搜索执行ID..."
        emptyText="暂无任务数据"
      />
    </div>
  );
}
