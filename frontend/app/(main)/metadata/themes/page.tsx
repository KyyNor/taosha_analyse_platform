"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getThemes } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { FolderOpen } from "lucide-react";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getThemes();
      setData(Array.isArray(res?.data) ? res.data : res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // 表格列配置
  const columns = [
    { key: "id", label: "主题ID", type: "number" as const },
    { key: "theme_name", label: "主题名称", type: "text" as const },
    { key: "theme_description", label: "主题描述", type: "text" as const, maxLength: 80 },
    { key: "theme_type", label: "主题类型", type: "text" as const },
    { key: "department", label: "关联部门", type: "text" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/themes/${item.id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/themes/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push('/metadata/themes/new');
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FolderOpen className="h-6 w-6" />
          数据主题管理
        </h1>
        <p className="text-muted-foreground">管理数据主题分类和层级结构</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索主题名称或描述..."
        emptyText="暂无数据主题"
      />
    </div>
  );
}