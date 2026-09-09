"use client";

/**
 * 通用配置页面
 *
 * 集中放置各功能模块的展示参数配置，后续新参数以卡片分区形式追加。
 * 当前分区：
 * - 命中记录指标展示：配置告警管控记录列表行内以 tag 形式展示的指标，
 *   配置顺序即展示顺序，对全部用户生效。
 */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { X, Save } from "lucide-react";
import { IndicatorMultiSelect, getIndicatorOptionDisplayName } from "@/components/fraudhunter/alert/IndicatorMultiSelect";
import type { IndicatorOption } from "@/components/fraudhunter/alert/IndicatorMultiSelect";
import { alertControlRecordService } from "@/lib/services/fraudhunter/alertControlRecordService";
import { indicatorService } from "@/lib/services/fraudhunterService";

export default function GeneralConfigPage() {
  // ============ 分区一：命中记录指标展示 ============
  const [indicators, setIndicators] = useState<IndicatorOption[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [indicatorList, tagConfig] = await Promise.all([
          indicatorService.list({ query_type: "all" }),
          alertControlRecordService.getIndicatorTagConfig(),
        ]);
        setIndicators(indicatorList.items || []);
        setSelectedCodes((tagConfig.indicators || []).map(i => i.indicator_code));
      } catch (error) {
        console.error("加载通用配置失败:", error);
        toast.error("加载配置失败");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const getChipLabel = (code: string) => {
    const indicator = indicators.find(i => i.indicator_code === code);
    return indicator ? getIndicatorOptionDisplayName(indicator) : code;
  };

  const removeCode = (code: string) => {
    setSelectedCodes(prev => prev.filter(c => c !== code));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await alertControlRecordService.updateIndicatorTagConfig(selectedCodes);
      toast.success("命中记录指标展示配置已保存");
    } catch (error) {
      console.error("保存命中记录指标展示配置失败:", error);
      toast.error("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">通用配置</h1>
        <p className="text-muted-foreground">各功能模块的展示参数配置，对全部用户生效</p>
      </div>

      {/* 分区一：命中记录指标展示 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>命中记录指标展示</CardTitle>
          <CardDescription>
            配置后告警管控记录列表将增加「指标值」列，按配置顺序以 tag
            形式展示命中时刻的指标快照值；Excel 导出同步追加对应列。
            清空列表并保存即关闭该列展示。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <IndicatorMultiSelect
              selectedCodes={selectedCodes}
              onChange={setSelectedCodes}
              indicators={indicators}
              placeholder="添加展示指标"
            />
            <Button onClick={handleSave} disabled={saving || loading}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? "保存中..." : "保存配置"}
            </Button>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">配置加载中...</p>
          ) : selectedCodes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              尚未配置展示指标，列表页不显示「指标值」列
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {selectedCodes.map(code => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
                >
                  {getChipLabel(code)}
                  <button
                    type="button"
                    aria-label={`移除 ${getChipLabel(code)}`}
                    className="ml-0.5 rounded-full hover:bg-blue-200 p-0.5"
                    onClick={() => removeCode(code)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            说明：展示的是命中时刻的指标快照值；指标改名后历史记录可能无法匹配，
            对应 tag 将显示为「指标名:—」。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
