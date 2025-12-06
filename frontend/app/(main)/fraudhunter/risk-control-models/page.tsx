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
import { riskControlModelService } from "@/lib/services/fraudhunterService";
import type {
  RiskControlModel,
  ObjectType,
  ModelStatus
} from "@/types/fraudhunter/risk-control-model";
import {
  getObjectTypeLabel,
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
  const [objectTypeFilter, setObjectTypeFilter] = useState<string>("all");
  const [codeFilter, setCodeFilter] = useState<string>("");

  // 加载预警管控模型列表
  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (objectTypeFilter !== "all") params.object_type = objectTypeFilter;
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
  }, [statusFilter, objectTypeFilter, codeFilter]);

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "model_code", label: "模型编码", type: "text" as const },
    { key: "model_name", label: "模型名称", type: "text" as const },
    {
      key: "object_type",
      label: "对象类型",
      type: "text" as const,
      render: (value: ObjectType) => (
        <Badge variant="outline">
          {getObjectTypeLabel(value)}
        </Badge>
      )
    },
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

  // 自定义操作按钮
  const customActions = (item: RiskControlModel) => (
    <>
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

        <Select value={objectTypeFilter} onValueChange={setObjectTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="对象类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="cust_no">客户号</SelectItem>
            <SelectItem value="dep_acct_no">存款账号</SelectItem>
            <SelectItem value="loan_acct_no">贷款账号</SelectItem>
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
    </div>
    </>
  );
}
