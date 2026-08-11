"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from 'sonner';
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Button } from "@/components/ui/button";
import { FileSpreadsheet } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ModelMultiSelect } from "@/components/fraudhunter/alert/ModelMultiSelect";
import { alertControlRecordService } from "@/lib/services/fraudhunter/alertControlRecordService";
import type {
  AlertControlRecord,
  AlertControlFilters
} from "@/lib/services/fraudhunter/alertControlRecordService";
import { alertStatusBadgeConfig, controlStatusBadgeConfig } from "@/lib/utils/badgeConfigs";
import { downloadFromResponse, generateTimestampedFilename } from "@/lib/utils/downloadUtils";
import { useAuth } from "@/hooks/useAuth";

// 允许查看详情的部门编号
const DETAIL_VIEW_DEPARTMENTS = ["110026", "110004"];

const formatDateForInput = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export default function AlertControlRecordsPage() {
  const router = useRouter();
  const { user } = useAuth();

  // 判断当前用户是否可以查看详情按钮
  const canViewDetail =
    !!user && DETAIL_VIEW_DEPARTMENTS.includes(user.branch_no);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AlertControlRecord[]>([]);
  const [exporting, setExporting] = useState(false);

  // 模型列表状态
  const [allModelIds, setAllModelIds] = useState<number[]>([]);

  // 筛选状态
  const [filters, setFilters] = useState<AlertControlFilters>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [hideInactive, setHideInactive] = useState(true);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 加载所有在线模型ID（用于默认全选）
  useEffect(() => {
    const loadModelIds = async () => {
      try {
        const { riskControlModelService } = await import('@/lib/services/fraudhunter/riskControlModelService');
        const response = await riskControlModelService.list({
          page: 1,
          page_size: 1000,
          status: 'online'
        });
        const modelIds = response.items?.map(m => m.id) || [];
        setAllModelIds(modelIds);
        // 默认全选所有模型
        setFilters(prev => ({ ...prev, model_ids: modelIds }));
      } catch (error) {
        console.error('加载模型列表失败:', error);
      }
    };
    loadModelIds();
  }, []);

  // 加载告警管控记录列表
  const loadRecords = async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        search: searchQuery.trim() || undefined,
        hide_inactive: hideInactive || undefined,
        ...filters,
      };

      const response = await alertControlRecordService.list(params);
      setData(response.records || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error("Failed to load alert control records:", error);
      toast.error("加载告警管控记录失败");
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [filters, searchQuery, currentPage, hideInactive]);

  // 筛选条件或搜索变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [filters, searchQuery, hideInactive]);

  // 分页处理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // 查看详情
  const handleView = (record: AlertControlRecord) => {
    router.push(`/fraudhunter/alert-control-records/${record.id}`);
  };

  // 导出数据
  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await alertControlRecordService.export({
        filters: { ...filters, search: searchQuery.trim() || undefined, hide_inactive: hideInactive || undefined },
        format: 'excel'
      });

      // 使用公共工具函数下载文件（优先使用后端传递的文件名）
      const defaultFilename = generateTimestampedFilename('alert_control_records', 'xlsx');
      downloadFromResponse(response, defaultFilename);

      toast.success('Excel 文件导出成功');
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("导出失败，请重试");
    } finally {
      setExporting(false);
    }
  };



  // 表格列配置
  const columns = [
    { key: "account_id", label: "账号", type: "text" as const, width: "160px" },
    { key: "record_date", label: "日期", type: "text" as const, width: "115px" },
    {
      key: "hit_model_names",
      label: "模型",
      type: "custom" as const,
      render: (value: string[]) => {
        if (!value || value.length === 0) return <span className="text-muted-foreground">-</span>;
        return (
          <div className="flex flex-wrap gap-1">
            {value.map((name, idx) => (
              <span
                key={idx}
                className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
              >
                {name}
              </span>
            ))}
          </div>
        );
      }
    },
    {
      key: "alert_status",
      label: "告警状态",
      type: "badge" as const,
      badgeConfig: alertStatusBadgeConfig,
      width: "100px"
    },
    {
      key: "control_status",
      label: "管控状态",
      type: "badge" as const,
      badgeConfig: controlStatusBadgeConfig,
      width: "100px"
    },
    { key: "control_serial_number", label: "管控流水号", type: "text" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const }
  ];

  // 获取今天的日期字符串
  const getTodayString = () => {
    return formatDateForInput(new Date());
  };

  // 获取一周前的日期字符串
  const getWeekAgoString = () => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return formatDateForInput(date);
  };

  // 允许从任一端调整日期范围；若发生倒序，自动同步另一端。
  const handleStartDateChange = (value: string) => {
    const startDate = value || undefined;
    setFilters((prev) => ({
      ...prev,
      start_date: startDate,
      end_date:
        startDate && prev.end_date && prev.end_date < startDate
          ? startDate
          : prev.end_date,
    }));
  };

  const handleEndDateChange = (value: string) => {
    const endDate = value || undefined;
    setFilters((prev) => ({
      ...prev,
      start_date:
        endDate && prev.start_date && prev.start_date > endDate
          ? endDate
          : prev.start_date,
      end_date: endDate,
    }));
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">告警管控记录</h1>
          <p className="text-muted-foreground">查看和管理模型执行的告警与管控记录</p>
        </div>
        <Button variant="outline" disabled={exporting} onClick={handleExport}>
          <FileSpreadsheet className="h-4 w-4 mr-2" />
          {exporting ? "导出中..." : "导出Excel"}
        </Button>
      </div>

      {/* 筛选器 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
            {/* 日期范围 */}
            <div className="space-y-2">
              <Label htmlFor="start_date">开始日期</Label>
              <Input
                id="start_date"
                type="date"
                value={filters.start_date || ""}
                onChange={(e) => handleStartDateChange(e.target.value)}
                max={getTodayString()}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="end_date">结束日期</Label>
              <Input
                id="end_date"
                type="date"
                value={filters.end_date || ""}
                onChange={(e) => handleEndDateChange(e.target.value)}
                max={getTodayString()}
              />
            </div>

            {/* 模型多选 */}
            <div className="space-y-2">
              <Label>筛选模型</Label>
              <ModelMultiSelect
                selectedIds={filters.model_ids || []}
                onChange={(ids) => setFilters(prev => ({ ...prev, model_ids: ids.length === allModelIds.length ? allModelIds : ids }))}
                placeholder="选择模型"
              />
            </div>

            {/* 告警状态筛选 */}
            <div className="space-y-2">
              <Label>告警状态</Label>
              <Select
                value={filters.alert_status || "all"}
                onValueChange={(value) => setFilters(prev => ({ ...prev, alert_status: value === "all" ? undefined : value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择告警状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="not_configured">未配置</SelectItem>
                  <SelectItem value="sent">已发送</SelectItem>
                  <SelectItem value="duplicate">重复告警</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* 管控状态筛选 */}
            <div className="space-y-2">
              <Label>管控状态</Label>
              <Select
                value={filters.control_status || "all"}
                onValueChange={(value) => setFilters(prev => ({ ...prev, control_status: value === "all" ? undefined : value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择管控状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="not_configured">未配置</SelectItem>
                  <SelectItem value="executed">已执行</SelectItem>
                  <SelectItem value="duplicate">重复管控</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 快速日期选择和过滤选项 */}
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = getTodayString();
                  setFilters(prev => ({ ...prev, start_date: today, end_date: today }));
                }}
              >
                今天
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFilters(prev => ({
                    ...prev,
                    start_date: getWeekAgoString(),
                    end_date: getTodayString()
                  }));
                }}
              >
                最近一周
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFilters({})}
              >
                重置筛选
              </Button>
            </div>

            {/* 隐藏无效记录 */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="hide_inactive"
                checked={hideInactive}
                onCheckedChange={(checked) => setHideInactive(checked === true)}
              />
              <Label
                htmlFor="hide_inactive"
                className="text-sm font-normal cursor-pointer"
              >
                隐藏无效记录（告警/管控均为重复或未配置）
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={loadRecords}
        onView={canViewDetail ? handleView : undefined}
        searchPlaceholder="搜索账号、模型等..."
        emptyText="暂无告警管控记录"
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
