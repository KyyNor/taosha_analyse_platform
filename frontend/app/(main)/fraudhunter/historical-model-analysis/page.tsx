"use client";

import { useState, useCallback, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { toast} from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LineChart } from "@/components/generative_ui/LineChart";
import { LineChartSkeleton } from "@/components/generative_ui/LineChart";
import { ModelMultiSelect } from "@/components/fraudhunter/alert/ModelMultiSelect";
import { alertControlRecordService } from "@/lib/services/fraudhunter/alertControlRecordService";
import type {
  TrendRequest,
  TrendResponse,
  TrendPoint,
  SeriesByModel,
  Granularity,
} from "@/lib/types/fraudhunter/historyAnalysis";
import { riskControlModelService } from "@/lib/services/fraudhunter/riskControlModelService";

export default function HistoricalModelAnalysisPage() {
  // ---------- 筛选状态 ----------
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [selectedModelIds, setSelectedModelIds] = useState<number[]>([]);

  // ---------- 数据状态 ----------
  const [loading, setLoading] = useState(false);
  const [rawSeries, setRawSeries] = useState<TrendPoint[]>([]);
  const [totalPoints, setTotalPoints] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ---------- 加载模型列表（初始全选）----------
  useEffect(() => {
    const loadModels = async () => {
      try {
        const resp = await riskControlModelService.list({
          page: 1,
          page_size: 1000,
          status: "online",
        });
        const ids = resp.items?.map((m) => m.id) ?? [];
        setSelectedModelIds(ids);
      } catch {
        toast.warning("模型列表加载失败，请手动选择模型后点击查询");
        // 用户仍可通过手动选择模型再点查询，不会造成完全不可用
      }
    };
    loadModels();
  }, []);

  // ---------- 发起查询 ----------
  const handleQuery = useCallback(async () => {
    if (!startDate || !endDate) {
      toast.error("请填写完整的日期范围");
      return;
    }
    if (startDate > endDate) {
      toast.error("开始日期不能晚于结束日期");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setRawSeries([]);

    const req: TrendRequest = {
      start_date: startDate,
      end_date: endDate,
      granularity,
      model_ids: selectedModelIds.length > 0 ? selectedModelIds : undefined,
    };

    try {
      const resp: TrendResponse =
        await alertControlRecordService.getModelHistoryTrend(req);
      setRawSeries(resp.series);
      setTotalPoints(resp.total_points);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "查询历史趋势失败，请稍后重试";
      setErrorMsg(String(detail));

      // 如果是"跨越太长"之类的服务端友好提示，也 toast
      if (typeof detail === "string" && !detail.includes("500")) {
        toast.warning(detail);
      } else {
        toast.error("查询失败");
      }
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, granularity, selectedModelIds]);

  // 自动首次查询
  useEffect(() => {
    if (selectedModelIds.length > 0) {
      handleQuery();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 仅首次 mounted 时触发

  // ---------- 快捷日期填充 ----------
  const fillQuickRange = (days: number) => {
    const ed = new Date();
    const sd = new Date();
    sd.setDate(ed.getDate() - days);
    setStartDate(sd.toISOString().slice(0, 10));
    setEndDate(ed.toISOString().slice(0, 10));
  };

  const GRANULARITIES: { label: string; value: Granularity }[] = [
    { label: "按日", value: "day" },
    { label: "按周", value: "week" },
    { label: "按月", value: "month" },
  ];

  // ---------- 图表数据转换 ----------
  // 过滤只保留选中的模型（因为后端可能返回更多模型的数据）
  const filteredSeries = rawSeries.filter(
    (pt) =>
      selectedModelIds.length === 0 || selectedModelIds.includes(pt.model_id)
  );

  // 按 model_id 分组，每组取最大值代表该天/周的区间独立账户峰值
  const MODEL_COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
    "#84cc16",
    "#f97316",
    "#14b8a6",
  ];
  const groupedByModel = filteredSeries.reduce<
    Map<number, { name: string; color: string; points: TrendPoint[]; sum: number; max: number }>
  >((acc, pt) => {
    if (!acc.has(pt.model_id)) {
      acc.set(pt.model_id, {
        name: pt.model_name,
        color: MODEL_COLORS[(acc.size * 7 + pt.model_id) % MODEL_COLORS.length],
        points: [],
        sum: 0,
        max: 0,
      });
    }
    const grp = acc.get(pt.model_id)!;
    grp.points.push(pt);
    grp.sum += pt.distinct_account_count;
    grp.max = Math.max(grp.max, pt.distinct_account_count);
    return acc;
  }, new Map());

  const seriesByModel: SeriesByModel[] = Array.from(groupedByModel.values()).map(
    (g) => ({ model_id: g.points[0]?.model_id ?? 0, model_name: g.name, color: g.color, points: g.points, totalDistinctAccountCount: g.sum })
  );

  // 折线图所需格式：以 name=date_point 为 x 轴，各模型 name 为 y_key
  // 思路：从 seriesByModel 构建  x_labels 排序列表，再逐模型拼接
  const xLabels = [
    ...new Set(filteredSeries.map((p) => p.date_point)),
  ].sort();

  const chartData = xLabels.map((dp) => {
    const rec: Record<string, string | number> = { name: dp };
    seriesByModel.forEach((sg) => {
      const pt = sg.points.find((p) => p.date_point === dp);
      rec[sg.model_name] = pt?.distinct_account_count ?? 0;
    });
    return rec;
  });

  const chartColors = seriesByModel.map((sg) => sg.color);
  const chartYKeys = seriesByModel.map((sg) => sg.model_name);

  return (
    <div className="p-6 space-y-6">

      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <RefreshCw className="w-5 h-5 text-muted-foreground" />
        <h1 className="text-xl font-semibold">历史模型分析</h1>
      </div>

      {/* 筛选工具栏 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">

            {/* 起止日期 */}
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">开始日期</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">结束日期</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            {/* 粒度选择 */}
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">时间粒度</Label>
              <div className="flex gap-1">
                {GRANULARITIES.map((opt) => (
                  <Button
                    key={opt.value}
                    size="sm"
                    variant={granularity === opt.value ? "default" : "outline"}
                    onClick={() => setGranularity(opt.value)}
                    className="flex-1 text-xs"
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* 模型多选 */}
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">选择模型</Label>
              <ModelMultiSelect
                selectedIds={selectedModelIds}
                onChange={setSelectedModelIds}
              />
            </div>
          </div>

          {/* 快捷日期 + 查询 */}
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => fillQuickRange(7)}>
              近7天
            </Button>
            <Button size="sm" variant="outline" onClick={() => fillQuickRange(30)}>
              近30天
            </Button>
            <Button size="sm" variant="outline" onClick={() => fillQuickRange(90)}>
              近90天
            </Button>
            <div className="flex-1" />
            <Button onClick={handleQuery} disabled={loading}>
              {loading ? "查询中…" : "查询"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 统计卡片行 */}
      {!loading && seriesByModel.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {seriesByModel.map((sg) => (
            <Card key={sg.model_id} className="overflow-hidden">
              <CardContent className="p-4">
                {/* 色块条 */}
                <div
                  className="h-1 rounded-full mb-3"
                  style={{ backgroundColor: sg.color }}
                />
                <div className="text-sm font-medium truncate mb-1" title={sg.model_name}>
                  {sg.model_name}
                </div>
                <div className="text-2xl font-bold" style={{ color: sg.color }}>
                  {sg.totalDistinctAccountCount.toLocaleString()}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  独立账户（合计）
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 主力图表区 */}
      {loading ? (
        <LineChartSkeleton />
      ) : errorMsg && !rawSeries.length ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
          <strong>接口错误：</strong>{errorMsg}
        </div>
      ) : rawSeries.length === 0 && !loading ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-sm text-muted-foreground">
          暂无数据，请调整筛选条件后重新查询
        </div>
      ) : (
        seriesByModel.length > 0 && (
          <LineChart
            title={`模型命中账户趋势${chartYKeys.length > 0 ? `（${chartYKeys.join(" / ")}）` : ""}`}
            description={`${startDate} 至 ${endDate}，共 ${totalPoints} 个${granularity === "day" ? "天" : granularity === "week" ? "周" : "月"}，${chartYKeys.length} 个模型`}
            data={chartData}
            x_key="name"
            y_keys={chartYKeys}
            colors={chartColors}
            area={true}
            height={380}
          />
        )
      )}
    </div>
  );
}