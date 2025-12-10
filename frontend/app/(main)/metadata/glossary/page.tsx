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

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getGlossary({ page: currentPage, page_size: pageSize });
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentPage]);

  // 分页处理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "术语ID", type: "number" as const },
    { key: "name", label: "术语名称", type: "text" as const },
    { key: "type", label: "术语类型", type: "text" as const },
    { key: "content", label: "内容配置", type: "object" as const, maxLength: 100 },
    { key: "creator", label: "创建者", type: "text" as const },
    { key: "is_basic", label: "基础术语", type: "boolean" as const },
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
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
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
        pagination={{
          pageSize,
          currentPage,
          total,
          onPageChange: handlePageChange,
        }}
      />
    </div>
  );
}