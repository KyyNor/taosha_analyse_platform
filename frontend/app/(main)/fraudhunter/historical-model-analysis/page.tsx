"use client";

import { useState, useCallback, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
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

// 日级粒度常量（主查询固定按日）
const DAY: Granularity = "day";

export default function HistoricalModelAnalysisPage() {
  // ---------- 筛选状态 ----------
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [selectedModelIds, setSelectedModelIds] = useState<number[]>([]);

  // ---------- 数据状态 ----------
  const [loading, setLoading] = useState(false);
  const [rawSeries, setRawSeries] = useState<TrendPoint[]>([]);
  const [totalPoints, setTotalPoints] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ---------- 弹窗状态 ----------
  const [dialogModelId, setDialogModelId] = useState<number | null>(null);
  const [dialogGranularity, setDialogGranularity] = useState<Granularity>("day");

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
      }
    };
    loadModels();
  }, []);

  // ---------- 发起查询（固定按日粒度）----------
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
      granularity: DAY,
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

      if (typeof detail === "string" && !detail.includes("500")) {
        toast.warning(detail);
      } else {
        toast.error("查询失败");
      }
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, selectedModelIds]);

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

  // ---------- 图例配色 ----------
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

  // ---------- 按模型分组 ----------
  const groupedByModel = rawSeries.reduce<
    Map<number, { name: string; color: string; points: TrendPoint[]; sum: number }>
  >((acc, pt) => {
    if (!acc.has(pt.model_id)) {
      acc.set(pt.model_id, {
        name: pt.model_name,
        color: MODEL_COLORS[(acc.size * 7 + pt.model_id) % MODEL_COLORS.length],
        points: [],
        sum: 0,
      });
    }
    const grp = acc.get(pt.model_id)!;
    grp.points.push(pt);
    grp.sum += pt.distinct_account_count;
    return acc;
  }, new Map());

  // 已选模型的统计数据（按命中数量倒序）
  const seriesByModel: SeriesByModel[] = Array.from(groupedByModel.entries())
    .filter(
      ([id]) =>
        selectedModelIds.length === 0 || selectedModelIds.includes(id)
    )
    .map(([id, g]) => ({
      model_id: id,
      model_name: g.name,
      color: g.color,
      points: g.points,
      totalDistinctAccountCount: g.sum,
    }))
    .sort((a, b) => b.totalDistinctAccountCount - a.totalDistinctAccountCount);

  // ---------- 弹窗内图表数据 ----------
  const dialogItem = dialogModelId != null
    ? seriesByModel.find((sg) => sg.model_id === dialogModelId)
    : null;

  // 根据弹窗粒度合并日级数据
  const dialogChartData = (() => {
    if (!dialogItem) return [];

    const pts = [...dialogItem.points].sort(
      (a, b) => a.date_point.localeCompare(b.date_point)
    );

    if (dialogGranularity === "day") {
      return pts.map((p) => ({ name: p.date_point, value: p.distinct_account_count }));
    }

    // 按 week 或 month 分组合并
    const map = new Map<string, number>();
    for (const p of pts) {
      const date = new Date(p.date_point.replace(/\./g, "-"));
      let key: string;
      if (dialogGranularity === "week") {
        // ISO year-week
        const y = date.getFullYear();
        const firstDay = new Date(y, 0, 1);
        const weekNum = Math.ceil(
          ((date.getTime() - firstDay.getTime()) / 86400000 + firstDay.getDay() + 1) / 7
        );
        key = `${y}年第${weekNum}周`;
      } else {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
      }
      map.set(key, (map.get(key) ?? 0) + p.distinct_account_count);
    }

    return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
  })();

  const GRANS: { label: string; value: Granularity }[] = [
    { label: "按日", value: "day" },
    { label: "按周", value: "week" },
    { label: "按月", value: "month" },
  ];

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
            {/* 开始日期 */}
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">开始日期</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            {/* 结束日期 */}
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-medium">结束日期</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            {/* 空占位，保持对齐 */}
            <div />
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
            <Button size="sm" variant="outline" onClick={() => fillQuickRange(180)}>
              近180天
            </Button>
            <div className="flex-1" />
            <Button onClick={handleQuery} disabled={loading}>
              {loading ? "查询中…" : "查询"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 统计卡片行（按命中数量倒序） */}
      {!loading && seriesByModel.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {seriesByModel.map((sg) => (
            <Card
              key={sg.model_id}
              className="overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => {
                setDialogModelId(sg.model_id);
                setDialogGranularity("day");
              }}
            >
              <CardContent className="p-4">
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
                  命中数（合计）点击查看趋势 →
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 空/错状态 */}
      {!loading && seriesByModel.length === 0 && !errorMsg && (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-sm text-muted-foreground">
          暂无数据，请调整筛选条件后重新查询
        </div>
      )}

      {errorMsg && !rawSeries.length && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
          <strong>接口错误：</strong>{errorMsg}
        </div>
      )}

      {loading && (
        <LineChartSkeleton />
      )}

      {/* 趋势图弹窗 */}
      <Dialog
        open={dialogModelId !== null}
        onOpenChange={(open) => !open && setDialogModelId(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{dialogItem?.model_name ?? ""}</DialogTitle>
            <DialogDescription>
              {startDate} 至 {endDate}，共 {dialogChartData.length} 个
              {dialogGranularity === "day" ? "日" : dialogGranularity === "week" ? "周" : "月"}数据
            </DialogDescription>
          </DialogHeader>

          {/* 粒度切换 */}
          <div className="flex gap-2 mb-2">
            {GRANS.map((opt) => (
              <Button
                key={opt.value}
                size="sm"
                variant={dialogGranularity === opt.value ? "default" : "outline"}
                onClick={() => setDialogGranularity(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>

          {/* 弹窗内图表 */}
          {dialogChartData.length > 0 ? (
            <LineChart
              title=""
              description=""
              data={dialogChartData.map((d) => ({ name: d.name, [dialogItem!.model_name]: d.value }))}
              x_key="name"
              y_keys={[dialogItem!.model_name]}
              colors={[dialogItem!.color]}
              area={true}
              height={320}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-muted-foreground">
              暂无数值
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}