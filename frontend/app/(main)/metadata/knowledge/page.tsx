"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getDocuments, deleteDocument } from "@/lib/services/knowledgeService";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { documentSourceTypeBadgeConfig, documentProcessingStatusBadgeConfig } from "@/lib/utils/badgeConfigs";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();
  const { confirm } = useConfirmDialog();

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>("");

  const load = async () => {
    setLoading(true);
    try {
      const params: any = { page: currentPage, page_size: pageSize };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (sourceTypeFilter) params.source_type = sourceTypeFilter;

      const res = await getDocuments(params);
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } catch (error) {
      console.error("加载文档列表失败:", error);
      toast.error("加载文档列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentPage, searchQuery, sourceTypeFilter]);

  // 搜索变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, sourceTypeFilter]);

  // 分页处理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "文档ID", type: "number" as const },
    { key: "title", label: "文档标题", type: "text" as const },
    {
      key: "source_type",
      label: "源类型",
      type: "badge" as const,
      badgeConfig: documentSourceTypeBadgeConfig
    },
    {
      key: "processing_status",
      label: "处理状态",
      type: "badge" as const,
      badgeConfig: documentProcessingStatusBadgeConfig
    },
    { key: "fragment_count", label: "片段数", type: "number" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/knowledge/${item.id}`);
  };

  const handleAdd = () => {
    router.push('/metadata/knowledge/new');
  };

  const handleDelete = async (item: any, index: number) => {
    confirm({
      title: "确认删除",
      description: `确定要删除文档"${item.title}"吗？删除后无法恢复，其关联的所有片段也将被删除。`,
      variant: "destructive",
      onConfirm: async () => {
        try {
          await deleteDocument(item.id);
          toast.success("文档删除成功");
          load();
        } catch (error) {
          console.error("删除文档失败:", error);
          toast.error("删除文档失败，请重试");
        }
      }
    });
  };

  // 源类型过滤器选项
  const sourceTypeOptions = [
    { value: "", label: "全部类型" },
    { value: "file", label: "文件" },
    { value: "text", label: "文本" },
    { value: "sql", label: "SQL" }
  ];

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BookOpen className="h-6 w-6" />
          知识库管理
        </h1>
        <p className="text-muted-foreground">管理知识文档，支持LLM自动生成和主题提取</p>
      </div>

      {/* 源类型过滤器 */}
      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm text-muted-foreground">源类型:</label>
        <select
          value={sourceTypeFilter}
          onChange={(e) => setSourceTypeFilter(e.target.value)}
          className="px-3 py-1.5 border border-input rounded-md text-sm bg-background"
        >
          {sourceTypeOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onDelete={handleDelete}
        searchPlaceholder="搜索文档标题..."
        emptyText="暂无文档数据"
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
