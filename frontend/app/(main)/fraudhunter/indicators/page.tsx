"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { indicatorService, indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { Indicator, IndicatorTask } from "@/lib/services/fraudhunterService";

export default function IndicatorsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Indicator[]>([]);
  const [IndicatorTasks, setIndicatorTasks] = useState<IndicatorTask[]>([]);

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [taskFilter, setTaskFilter] = useState<string>("all");

  // 加载指标任务列表用于筛选
  const loadIndicatorTasks = async () => {
    try {
      const response = await indicatorTaskService.list({});
      setIndicatorTasks(response.items || []);
    } catch (error) {
      console.error("Failed to load indicator tasks:", error);
    }
  };

  // 加载指标列表
  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (typeFilter !== "all") params.indicator_type = typeFilter;
      if (taskFilter !== "all") params.indicator_task_id = Number(taskFilter);

      const response = await indicatorService.list(params);
      setData(response.items || []);
    } catch (error) {
      console.error("Failed to load indicators:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIndicatorTasks();
  }, []);

  useEffect(() => {
    load();
  }, [statusFilter, typeFilter, taskFilter]);

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "indicator_code", label: "指标编码", type: "text" as const },
    { key: "indicator_name", label: "指标名称", type: "text" as const },
    {
      key: "indicator_type",
      label: "类型",
      type: "text" as const,
      render: (value: string) => (
        <Badge variant="outline">
          {value === "offline" ? "离线" : "实时"}
        </Badge>
      )
    },
    {
      key: "data_type",
      label: "数据类型",
      type: "text" as const,
      render: (value: string) => {
        const labels: Record<string, string> = {
          numeric: "数值",
          enum: "枚举",
          text: "文本",
          boolean: "布尔"
        };
        return <span>{labels[value] || value}</span>;
      }
    },
    { key: "indicator_task_id", label: "指标任务ID", type: "number" as const },
    {
      key: "status",
      label: "状态",
      type: "text" as const,
      render: (value: string) => {
        const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
          draft: "secondary",
          testing: "default",
          online: "default",
          offline: "outline",
          archived: "destructive"
        };
        return <Badge variant={variants[value] || "default"}>{value}</Badge>;
      }
    },
    { key: "current_version", label: "版本", type: "number" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const }
  ];

  // 操作处理
  const handleView = (item: Indicator) => {
    router.push(`/fraudhunter/indicators/${item.id}`);
  };

  const handleEdit = (item: Indicator) => {
    router.push(`/fraudhunter/indicators/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push("/fraudhunter/indicators/new");
  };

  const handleDelete = async (item: Indicator) => {
    try {
      await indicatorService.delete(item.id);
      await load();
    } catch (error: any) {
      console.error("Failed to delete indicator:", error);
      alert(error.response?.data?.detail || "删除失败");
    }
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">指标管理</h1>
        <p className="text-muted-foreground">管理反诈指标定义</p>
      </div>

      {/* 筛选器 */}
      <div className="flex gap-4 mb-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="testing">测试中</SelectItem>
            <SelectItem value="online">在线</SelectItem>
            <SelectItem value="offline">离线</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="offline">离线</SelectItem>
            <SelectItem value="realtime">实时</SelectItem>
          </SelectContent>
        </Select>

        <Select value={taskFilter} onValueChange={setTaskFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="指标任务筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部指标任务</SelectItem>
            {IndicatorTasks.map((task) => (
              <SelectItem key={task.id} value={String(task.id)}>
                {task.task_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="搜索指标编码或名称..."
        emptyText="暂无指标数据"
      />
    </div>
  );
}
