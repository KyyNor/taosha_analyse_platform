"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from 'sonner';
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
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
import { riskControlModelService } from "@/lib/services/fraudhunterService";
import type {
  RiskControlModel,
  ModelStatus
} from "@/types/fraudhunter/risk-control-model";
import {
  getModelStatusLabel,
  getModelStatusVariant
} from "@/types/fraudhunter/risk-control-model";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function RiskControlModelsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RiskControlModel[]>([]);
  const { confirm, DialogComponent } = useConfirmDialog();

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [codeFilter, setCodeFilter] = useState<string>("");

  // 历史回测对话框状态
  const [backtestDialogOpen, setBacktestDialogOpen] = useState(false);
  const [backtestModel, setBacktestModel] = useState<RiskControlModel | null>(null);
  const [backtestStartDate, setBacktestStartDate] = useState<string>("");
  const [backtestEndDate, setBacktestEndDate] = useState<string>("");
  const [backtestLoading, setBacktestLoading] = useState(false);

  // 加载预警管控模型列表
  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (codeFilter) params.model_code = codeFilter;

      const response = await riskControlModelService.list(params);
      setData(response.items || []);
    } catch (error) {
      console.error("Failed to load risk control models:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter, codeFilter]);

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "model_code", label: "模型编码", type: "text" as const },
    { key: "model_name", label: "模型名称", type: "text" as const },
    {
      key: "status",
      label: "状态",
      type: "text" as const,
      render: (value: ModelStatus) => (
        <Badge variant={getModelStatusVariant(value)}>
          {getModelStatusLabel(value)}
        </Badge>
      )
    },
    { key: "current_version", label: "当前版本", type: "number" as const },
    { key: "latest_version", label: "最新版本", type: "number" as const },
    {
      key: "is_send_alert_message",
      label: "发送告警",
      type: "text" as const,
      render: (value: boolean) => (
        <span>{value ? "是" : "否"}</span>
      )
    },
    {
      key: "is_acct_control",
      label: "账户控制",
      type: "text" as const,
      render: (value: boolean) => (
        <span>{value ? "是" : "否"}</span>
      )
    },
    { key: "created_at", label: "创建时间", type: "datetime" as const }
  ];

  // 操作处理
  const handleView = (item: RiskControlModel) => {
    router.push(`/fraudhunter/risk-control-models/${item.id}`);
  };

  const handleEdit = (item: RiskControlModel) => {
    router.push(`/fraudhunter/risk-control-models/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push("/fraudhunter/risk-control-models/new");
  };

  const handleDelete = async (item: RiskControlModel) => {
    confirm({
      title: "确认删除",
      description: `确定要删除模型 "${item.model_name}" 吗？`,
      onConfirm: async () => {
        try {
          await riskControlModelService.delete(item.id);
          await load();
        } catch (error: any) {
          console.error("Failed to delete risk control model:", error);
          toast.error(error.response?.data?.detail || "删除失败");
        }
      },
      variant: "destructive"
    });
  };

  const handlePublish = async (item: RiskControlModel) => {
    const version = prompt(
      `请输入要发布的版本号 (1-${item.latest_version}):`,
      String(item.latest_version)
    );

    if (!version) return;

    const versionNum = parseInt(version);
    if (isNaN(versionNum) || versionNum < 1 || versionNum > item.latest_version) {
      toast.error("无效的版本号");
      return;
    }

    const description = prompt("请输入变更说明（可选）:");

    try {
      await riskControlModelService.publish(item.id, {
        version: versionNum,
        change_description: description || undefined
      });
      await load();
      toast.success("发布成功");
    } catch (error: any) {
      console.error("Failed to publish risk control model:", error);
      toast.error(error.response?.data?.detail || "发布失败");
    }
  };

  const handleArchive = async (item: RiskControlModel) => {
    confirm({
      title: "确认归档",
      description: `确定要归档模型 "${item.model_name}" 吗？`,
      onConfirm: async () => {
        try {
          await riskControlModelService.archive(item.id);
          await load();
          toast.success("归档成功");
        } catch (error: any) {
          console.error("Failed to archive risk control model:", error);
          toast.error(error.response?.data?.detail || "归档失败");
        }
      },
      variant: "default"
    });
  };

  // 打开历史回测对话框
  const handleOpenBacktestDialog = (item: RiskControlModel) => {
    setBacktestModel(item);
    // 默认日期：过去7天
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);
    setBacktestStartDate(startDate.toISOString().split('T')[0]);
    setBacktestEndDate(endDate.toISOString().split('T')[0]);
    setBacktestDialogOpen(true);
  };

  // 提交历史回测任务
  const handleSubmitBacktest = async () => {
    if (!backtestModel) return;
    
    if (!backtestStartDate || !backtestEndDate) {
      toast.error("请选择开始日期和结束日期");
      return;
    }

    if (new Date(backtestStartDate) > new Date(backtestEndDate)) {
      toast.error("开始日期不能晚于结束日期");
      return;
    }

    setBacktestLoading(true);
    try {
      const response = await riskControlModelService.backtest(backtestModel.id, {
        start_date: backtestStartDate,
        end_date: backtestEndDate
      });

      if (response.success) {
        toast.success(response.message);
        setBacktestDialogOpen(false);
        // 提示用户可以在试运行任务页面查看进度
        toast.info("可在「试运行任务」页面查看任务进度", {
          action: {
            label: "前往查看",
            onClick: () => router.push("/fraudhunter/dry-run")
          }
        });
      } else {
        toast.error(response.message || "提交失败");
      }
    } catch (error: any) {
      console.error("Failed to submit backtest:", error);
      toast.error(error.response?.data?.detail || "提交历史回测任务失败");
    } finally {
      setBacktestLoading(false);
    }
  };

  // 自定义操作按钮
  const customActions = (item: RiskControlModel) => (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleOpenBacktestDialog(item)}
        disabled={item.status === "archived"}
        title="历史回测"
      >
        回测
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handlePublish(item)}
        disabled={item.status === "archived"}
        title="发布"
      >
        发布
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleArchive(item)}
        disabled={item.status === "archived"}
        title="归档"
      >
        归档
      </Button>
    </>
  );

  return (
    <>
      <DialogComponent />
      <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">预警管控模型管理</h1>
        <p className="text-muted-foreground">管理FraudHunter预警管控模型定义</p>
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
            <SelectItem value="online">已上线</SelectItem>
            <SelectItem value="offline">已下线</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>

        <input
          type="text"
          placeholder="模型编码搜索..."
          value={codeFilter}
          onChange={(e) => setCodeFilter(e.target.value)}
          className="px-3 py-2 border border-input rounded-md bg-background"
        />
      </div>

      {/* 表格 */}
      <MetadataTable
        columns={columns}
        data={data}
        loading={loading}
        onView={handleView}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onAdd={handleAdd}
        customActions={customActions}
      />

      {/* 历史回测对话框 */}
      <Dialog open={backtestDialogOpen} onOpenChange={setBacktestDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>模型历史回测</DialogTitle>
            <DialogDescription>
              {backtestModel && (
                <>
                  对模型 <strong>{backtestModel.model_name}</strong> ({backtestModel.model_code}) 进行历史回测。
                  回测任务将在后台执行，可在「试运行任务」页面查看进度。
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="startDate" className="text-right">
                开始日期
              </Label>
              <Input
                id="startDate"
                type="date"
                value={backtestStartDate}
                onChange={(e) => setBacktestStartDate(e.target.value)}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="endDate" className="text-right">
                结束日期
              </Label>
              <Input
                id="endDate"
                type="date"
                value={backtestEndDate}
                onChange={(e) => setBacktestEndDate(e.target.value)}
                className="col-span-3"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setBacktestDialogOpen(false)}
              disabled={backtestLoading}
            >
              取消
            </Button>
            <Button
              onClick={handleSubmitBacktest}
              disabled={backtestLoading}
            >
              {backtestLoading ? "提交中..." : "提交回测任务"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </>
  );
}
