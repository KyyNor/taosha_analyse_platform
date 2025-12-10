"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getFineReports, deleteFineReport, type FineReport } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function FineReportsPage() {
  const { confirm, DialogComponent } = useConfirmDialog();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<FineReport[]>([]);
  const [filters, setFilters] = useState<{
    is_available?: number;
    report_type?: string;
    department_id?: number;
    keyword?: string;
  }>({});
  const router = useRouter();

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getFineReports({
        ...filters,
        page: currentPage,
        page_size: pageSize
      });
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } catch (error) {
      console.error("加载FineReport报表失败:", error);
      toast.error("加载报表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filters, currentPage]);

  // 筛选条件变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [filters]);

  // 分页处理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "报表ID", type: "number" as const },
    { key: "report_name", label: "报表名称", type: "text" as const },
    {
      key: "report_type",
      label: "报表类型",
      type: "text" as const,
      render: (value: string) => value === 'summary' ? '汇总表' : '明细表'
    },
    { key: "report_design_address", label: "设计器地址", type: "text" as const, maxLength: 30 },
    { key: "department_id", label: "部门ID", type: "number" as const },
    { key: "description", label: "报表说明", type: "text" as const, maxLength: 50 },
    { key: "is_available", label: "是否可用", type: "boolean" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: FineReport) => {
    router.push(`/metadata/fine-reports/${item.id}`);
  };

  const handleEdit = (item: FineReport) => {
    router.push(`/metadata/fine-reports/${item.id}?mode=edit`);
  };

  const handleDelete = (item: FineReport) => {
    confirm({
      title: "确认删除",
      description: `确定要删除报表"${item.report_name}"吗？`,
      variant: "destructive",
      onConfirm: async () => {
        try {
          await deleteFineReport(item.id);
          toast.success("删除报表成功");
          load();
        } catch (error) {
          console.error("删除报表失败:", error);
          toast.error("删除报表失败");
        }
      }
    });
  };

  const handleAdd = () => {
    router.push(`/metadata/fine-reports/new`);
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">FineReport报表管理</h1>
        <p className="text-muted-foreground">管理系统中的FineReport报表元数据</p>
      </div>

      {/* 过滤器 */}
      <div className="flex gap-4 mb-6 p-4 bg-card rounded-lg border">
        <div className="flex-1">
          <label className="text-sm font-medium mb-2 block">报表类型</label>
          <select
            value={filters.report_type || ""}
            onChange={(e) => setFilters({ ...filters, report_type: e.target.value || undefined })}
            className="w-full px-3 py-2 border rounded-md bg-background"
          >
            <option value="">全部</option>
            <option value="summary">汇总表</option>
            <option value="detail">明细表</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-sm font-medium mb-2 block">可用状态</label>
          <select
            value={filters.is_available ?? ""}
            onChange={(e) => setFilters({ ...filters, is_available: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full px-3 py-2 border rounded-md bg-background"
          >
            <option value="">全部</option>
            <option value="0">可用</option>
            <option value="1">不可用</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-sm font-medium mb-2 block">关键词搜索</label>
          <input
            type="text"
            value={filters.keyword || ""}
            onChange={(e) => setFilters({ ...filters, keyword: e.target.value || undefined })}
            placeholder="搜索报表名称、描述..."
            className="w-full px-3 py-2 border rounded-md bg-background"
          />
        </div>
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
        searchPlaceholder="搜索报表名称或描述..."
        emptyText="暂无FineReport报表数据"
        pagination={{
          pageSize,
          currentPage,
          total,
          onPageChange: handlePageChange,
        }}
      />
      <DialogComponent />
    </div>
  );
}
