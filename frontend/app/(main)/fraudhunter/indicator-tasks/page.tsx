"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Rocket, RefreshCw } from "lucide-react";
import { indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { IndicatorTask } from "@/lib/services/fraudhunterService";
import { toast } from "sonner";

export default function IndicatorTasksPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<IndicatorTask[]>([]);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState<string>("");

  // 上线对话框状态
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<IndicatorTask | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);

  // 补数对话框状态
  const [rerunDialogOpen, setRerunDialogOpen] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isRerunning, setIsRerunning] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const response = await indicatorTaskService.list(params);
      setData(response.items || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error("Failed to load indicator tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentPage, searchQuery]);

  // 搜索变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // 分页处理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "task_code", label: "指标任务编码", type: "text" as const },
    { key: "task_name", label: "指标任务名称", type: "text" as const },
    {
      key: "object_type",
      label: "对象类型",
      type: "text" as const,
      render: (value: string) => {
        const labels: Record<string, string> = {
          cust_no: "客户号",
          dep_acct_no: "存款账号",
          loan_acct_no: "贷款账号"
        };
        return <span>{labels[value] || value}</span>;
      }
    },
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
    { key: "current_version", label: "当前版本", type: "number" as const },
    { key: "latest_version", label: "最新版本", type: "number" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const }
  ];

  // 操作处理
  const handleView = (item: IndicatorTask) => {
    router.push(`/fraudhunter/indicator-tasks/${item.id}`);
  };

  const handleEdit = (item: IndicatorTask) => {
    router.push(`/fraudhunter/indicator-tasks/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push("/fraudhunter/indicator-tasks/new");
  };

  const handleDelete = async (item: IndicatorTask) => {
    try {
      await indicatorTaskService.delete(item.id);
      // 重新加载列表
      await load();
    } catch (error: any) {
      console.error("Failed to delete indicator task:", error);
      toast.error(error.response?.data?.detail || "删除失败");
    }
  };

  // 打开上线对话框
  const handlePublishToDS = (item: IndicatorTask) => {
    setSelectedTask(item);
    setPublishDialogOpen(true);
  };

  // 执行上线
  const handleConfirmPublish = async () => {
    if (!selectedTask) return;

    setIsPublishing(true);
    try {
      const result = await indicatorTaskService.publishToDS(selectedTask.id, {});

      if (result.success) {
        toast.success(`上线成功！工作流名称：${result.workflow_name}, DS任务编号：${result.ds_task_code}`);
        setPublishDialogOpen(false);
        // 重新加载列表
        await load();
      } else {
        toast.error(`上线失败：${result.message}`);
      }
    } catch (error: any) {
      console.error("Failed to publish to DS:", error);
      toast.error(error.response?.data?.detail || "上线失败");
    } finally {
      setIsPublishing(false);
    }
  };

  // 打开补数对话框
  const handleRerun = (item: IndicatorTask) => {
    setSelectedTask(item);
    // 默认开始日期为昨天
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    setStartDate(yesterday.toISOString().split('T')[0]);
    setEndDate("");
    setRerunDialogOpen(true);
  };

  // 执行补数
  const handleConfirmRerun = async () => {
    if (!selectedTask || !startDate) {
      toast.warning("请填写开始日期");
      return;
    }

    setIsRerunning(true);
    try {
      const result = await indicatorTaskService.rerun(selectedTask.id, {
        start_date: startDate,
        end_date: endDate || undefined,
      });

      if (result.success) {
        toast.success(`补数任务已提交！开始日期：${result.start_date}, 结束日期：${result.end_date || "今天"}`);
        setRerunDialogOpen(false);
      } else {
        toast.error(`补数失败：${result.message}`);
      }
    } catch (error: any) {
      console.error("Failed to rerun task:", error);
      toast.error(error.response?.data?.detail || "补数失败");
    } finally {
      setIsRerunning(false);
    }
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">指标任务管理</h1>
        <p className="text-muted-foreground">管理反诈指标任务及其SQL加工逻辑</p>
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
        searchPlaceholder="搜索指标任务编码或名称..."
        emptyText="暂无指标任务数据"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        pagination={{
          pageSize,
          currentPage,
          total,
          onPageChange: handlePageChange,
        }}
        customActions={(item: IndicatorTask) => (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePublishToDS(item)}
            >
              <Rocket className="h-4 w-4 mr-1" />
              上线
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleRerun(item)}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              补数
            </Button>
          </div>
        )}
      />

      {/* 上线对话框 */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>上线到 DolphinScheduler</DialogTitle>
            <DialogDescription>
              将指标任务 {selectedTask?.task_name} 上线到 DolphinScheduler 调度系统
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              确认上线后，系统将：
            </p>
            <ul className="list-disc list-inside text-sm text-muted-foreground mt-2 space-y-1">
              <li>自动创建/更新工作流</li>
              <li>生成表检查节点和 SQL 计算节点</li>
              <li>配置定时调度</li>
            </ul>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPublishDialogOpen(false)}
              disabled={isPublishing}
            >
              取消
            </Button>
            <Button
              onClick={handleConfirmPublish}
              disabled={isPublishing}
            >
              {isPublishing ? "上线中..." : "确认上线"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 补数对话框 */}
      <Dialog open={rerunDialogOpen} onOpenChange={setRerunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>补数</DialogTitle>
            <DialogDescription>
              对指标任务 {selectedTask?.task_name} 进行历史数据补数
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="start-date">开始日期 *</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="end-date">结束日期（可选，默认今天）</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1"
              />
            </div>

            <p className="text-sm text-muted-foreground">
              补数将在 DolphinScheduler 中执行，请在 DS 系统中查看任务状态
            </p>
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
              disabled={isRerunning || !startDate}
            >
              {isRerunning ? "提交中..." : "确认补数"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
