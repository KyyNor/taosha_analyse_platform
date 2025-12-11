"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getPromptTemplates } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { FileText } from "lucide-react";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState<string>("");

  const load = async () => {
    setLoading(true);
    try {
      const params: any = { page: currentPage, page_size: pageSize };
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await getPromptTemplates(params);
      setData(res?.items || []);
      setTotal(res?.total || 0);
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
    { key: "id", label: "模板ID", type: "number" as const },
    { key: "name", label: "模板名称", type: "text" as const },
    { key: "fields", label: "字段配置", type: "object" as const, maxLength: 80 },
    { key: "template", label: "模板内容", type: "text" as const, maxLength: 100 },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/prompt-templates/${item.id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/prompt-templates/${item.id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push('/metadata/prompt-templates/new');
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          提示词模板管理
        </h1>
        <p className="text-muted-foreground">管理AI查询的提示词模板</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索模板名称或描述..."
        emptyText="暂无提示词模板"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
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