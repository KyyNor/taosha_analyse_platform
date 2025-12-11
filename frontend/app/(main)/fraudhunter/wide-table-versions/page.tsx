"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { wideTableVersionService } from "@/lib/services/fraudhunterService";
import type { WideTableVersion } from "@/lib/services/fraudhunterService";

export default function WideTableVersionsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<WideTableVersion[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [tableNameFilter, setTableNameFilter] = useState<string>("all");

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState<string>("");

  // 加载数据
  const load = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (statusFilter !== "all") params.status = statusFilter;
      if (tableNameFilter !== "all") params.wide_table_name = tableNameFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const response = await wideTableVersionService.list(params);
      setData(response.items || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error("Failed to load wide table versions:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter, tableNameFilter, searchQuery, page]);

  // 筛选条件或搜索变化时重置到第一页
  useEffect(() => {
    setPage(1);
  }, [statusFilter, tableNameFilter, searchQuery]);

  // 分页处理
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    {
      key: "wide_table_name",
      label: "宽表名称",
      type: "text" as const,
      render: (value: string) => {
        const labels: Record<string, string> = {
          dep_acct_wide_table: "存款账户宽表",
          cust_wide_table: "客户宽表",
          loan_acct_wide_table: "贷款账户宽表"
        };
        return (
          <Badge variant="outline">
            {labels[value] || value}
          </Badge>
        );
      }
    },
    {
      key: "version_hash",
      label: "版本号",
      type: "text" as const,
      render: (value: string) => (
        <code className="bg-muted px-2 py-1 rounded text-xs">
          {value?.substring(0, 8)}
        </code>
      )
    },
    {
      key: "indicator_metadata",
      label: "指标数量",
      type: "text" as const,
      render: (value: Record<string, any>) => {
        const count = value ? Object.keys(value).length : 0;
        return <span>{count} 个</span>;
      }
    },
    {
      key: "status",
      label: "状态",
      type: "text" as const,
      render: (value: string) => {
        const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
          current: "default",
          target: "secondary",
          history: "outline",
          skipped: "destructive"
        };
        const labels: Record<string, string> = {
          current: "当前版本",
          target: "目标版本",
          history: "历史版本",
          skipped: "已跳过"
        };
        return <Badge variant={variants[value] || "default"}>{labels[value] || value}</Badge>;
      }
    },
    {
      key: "current_at",
      label: "生效时间",
      type: "datetime" as const,
      render: (value: string | null) => {
        if (!value) return <span className="text-muted-foreground">-</span>;
        return <span>{new Date(value).toLocaleString()}</span>;
      }
    },
    { key: "created_at", label: "创建时间", type: "datetime" as const }
  ];

  // 操作处理
  const handleView = (item: WideTableVersion) => {
    router.push(`/fraudhunter/wide-table-versions/${item.version_hash}`);
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">指标宽表版本管理</h1>
        <p className="text-muted-foreground">
          查看指标宽表的版本状态、指标清单和执行进度
        </p>
      </div>

      {/* 筛选器 */}
      <div className="flex gap-4 mb-4">
        <Select value={tableNameFilter} onValueChange={setTableNameFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="宽表类型筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部宽表</SelectItem>
            <SelectItem value="dep_acct_wide_table">存款账户宽表</SelectItem>
            <SelectItem value="cust_wide_table">客户宽表</SelectItem>
            <SelectItem value="loan_acct_wide_table">贷款账户宽表</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="current">当前版本</SelectItem>
            <SelectItem value="target">目标版本</SelectItem>
            <SelectItem value="history">历史版本</SelectItem>
            <SelectItem value="skipped">已跳过</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onView={handleView}
        searchPlaceholder="搜索版本号..."
        emptyText="暂无宽表版本数据"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        pagination={{
          pageSize,
          currentPage: page,
          total,
          onPageChange: handlePageChange,
        }}
      />
    </div>
  );
}