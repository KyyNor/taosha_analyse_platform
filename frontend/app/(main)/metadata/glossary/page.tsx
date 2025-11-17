"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getGlossary } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getGlossary();
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
    { key: "id", label: "术语ID", type: "number" as const },
    { key: "term_name", label: "术语名称", type: "text" as const },
    { key: "term_definition", label: "术语定义", type: "text" as const, maxLength: 80 },
    { key: "business_domain", label: "业务域", type: "text" as const },
    { key: "content", label: "内容配置", type: "object" as const, maxLength: 100 },
    { key: "is_active", label: "是否启用", type: "boolean" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/glossary/${item.id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/glossary/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push('/metadata/glossary/new');
  };

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BookOpen className="h-6 w-6" />
          术语表管理
        </h1>
        <p className="text-muted-foreground">管理系统中的业务术语和数据定义</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索术语名称或定义..."
        emptyText="暂无术语表数据"
      />
    </div>
  );
}