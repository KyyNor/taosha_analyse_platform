"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getTables } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";

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
      const res = await getTables({
        fields: false,
        page: currentPage,
        page_size: pageSize
      }); // 优化查询，不返回字段信息
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
    { key: "id", label: "表ID", type: "number" as const },
    { key: "name", label: "表名", type: "text" as const },
    { key: "comment", label: "表描述", type: "text" as const, maxLength: 50 },
    { key: "remark", label: "备注", type: "text" as const, maxLength: 50 },
    { key: "is_available", label: "是否可用", type: "boolean" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/tables/${item.id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/tables/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push(`/metadata/tables/new`);
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
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