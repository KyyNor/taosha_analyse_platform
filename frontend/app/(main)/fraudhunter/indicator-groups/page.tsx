"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import { indicatorGroupService } from "@/lib/services/fraudhunterService";
import type { IndicatorGroup } from "@/lib/services/fraudhunterService";

export default function IndicatorGroupsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<IndicatorGroup[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const response = await indicatorGroupService.list({});
      setData(response.items || []);
    } catch (error) {
      console.error("Failed to load indicator groups:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    { key: "group_code", label: "指标组编码", type: "text" as const },
    { key: "group_name", label: "指标组名称", type: "text" as const },
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
  const handleView = (item: IndicatorGroup) => {
    router.push(`/fraudhunter/indicator-groups/${item.id}`);
  };

  const handleEdit = (item: IndicatorGroup) => {
    router.push(`/fraudhunter/indicator-groups/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push("/fraudhunter/indicator-groups/new");
  };

  const handleDelete = async (item: IndicatorGroup) => {
    try {
      await indicatorGroupService.delete(item.id);
      // 重新加载列表
      await load();
    } catch (error: any) {
      console.error("Failed to delete indicator group:", error);
      alert(error.response?.data?.detail || "删除失败");
    }
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">指标组管理</h1>
        <p className="text-muted-foreground">管理反诈指标组及其SQL加工逻辑</p>
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
        searchPlaceholder="搜索指标组编码或名称..."
        emptyText="暂无指标组数据"
      />
    </div>
  );
}
