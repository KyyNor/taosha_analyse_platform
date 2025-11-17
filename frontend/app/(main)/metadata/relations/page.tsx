"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getRelations } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { Link } from "lucide-react";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getRelations();
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
    { key: "config_id", label: "配置ID", type: "number" as const },
    { key: "source_table", label: "源表", type: "text" as const },
    { key: "source_column", label: "源字段", type: "text" as const },
    { key: "target_table", label: "目标表", type: "text" as const },
    { key: "target_column", label: "目标字段", type: "text" as const },
    { key: "relation_type", label: "关系类型", type: "text" as const },
    { key: "description", label: "描述", type: "text" as const, maxLength: 50 },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/relations/${item.config_id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/relations/${item.config_id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push('/metadata/relations/new');
  };

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Link className="h-6 w-6" />
          关系配置管理
        </h1>
        <p className="text-muted-foreground">管理数据表之间的关联关系配置</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索表名、字段或描述..."
        emptyText="暂无关系配置数据"
      />
    </div>
  );
}