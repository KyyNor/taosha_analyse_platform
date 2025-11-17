"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getTables } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getTables({ fields: false }); // 优化查询，不返回字段信息
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
    { key: "table_id", label: "表ID", type: "number" as const },
    { key: "table_name", label: "表名", type: "text" as const },
    { key: "table_comment", label: "表描述", type: "text" as const, maxLength: 50 },
    { key: "is_available", label: "是否可用", type: "boolean" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/tables/${item.table_id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/tables/${item.table_id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push(`/metadata/tables/new`);
  };

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">数据表管理</h1>
        <p className="text-muted-foreground">管理系统中的数据表信息</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索表名或描述..."
        emptyText="暂无数据表数据"
      />
    </div>
  );
}