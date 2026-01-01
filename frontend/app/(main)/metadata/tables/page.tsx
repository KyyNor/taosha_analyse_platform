"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getTables } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { isAvailableBadgeConfig } from "@/lib/utils/badgeConfigs";
import { Button } from "@/components/ui/button";

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

  // 筛选状态：null表示全部，0表示启用，1表示未启用
  const [filterAvailable, setFilterAvailable] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {
        fields: false,
        page: currentPage,
        page_size: pageSize,
        // 默认按is_available升序排序（启用的在前）
        order_by: "is_available",
        order_direction: "asc"
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      // 添加筛选参数
      if (filterAvailable !== null) params.is_available = filterAvailable;

      const res = await getTables(params); // 优化查询，不返回字段信息
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentPage, searchQuery, filterAvailable]);

  // 搜索或筛选变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterAvailable]);

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
    {
      key: "is_available",
      label: "是否启用",
      type: "badge" as const,
      badgeConfig: isAvailableBadgeConfig
    },
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

      {/* 筛选按钮 */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-sm text-muted-foreground">筛选：</span>
        <div className="flex gap-2">
          <Button
            variant={filterAvailable === null ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterAvailable(null)}
          >
            全部
          </Button>
          <Button
            variant={filterAvailable === 0 ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterAvailable(0)}
          >
            启用
          </Button>
          <Button
            variant={filterAvailable === 1 ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterAvailable(1)}
          >
            未启用
          </Button>
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
        searchPlaceholder="搜索表名或描述..."
        emptyText="暂无数据表数据"
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