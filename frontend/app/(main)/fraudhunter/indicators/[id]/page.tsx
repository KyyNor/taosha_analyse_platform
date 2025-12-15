"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { indicatorService, indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { Indicator, IndicatorUpdate, IndicatorTask } from "@/lib/services/fraudhunterService";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function IndicatorDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const indicatorId = Number(params?.id || 0);
  const mode = searchParams?.get("mode")||'view';
  const { confirm, DialogComponent } = useConfirmDialog();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === "edit");
  const [data, setData] = useState<Indicator | null>(null);
  const [originalData, setOriginalData] = useState<Indicator | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [IndicatorTasks, setIndicatorTasks] = useState<IndicatorTask[]>([]);

  // 加载指标任务列表
  const loadIndicatorTasks = async () => {
    try {
      const response = await indicatorTaskService.list({});
      setIndicatorTasks(response.items || []);
    } catch (error) {
      console.error("Failed to load indicator tasks:", error);
    }
  };

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await indicatorService.get(indicatorId);
      setData(result);
      setOriginalData(JSON.parse(JSON.stringify(result)));
    } catch (error) {
      console.error("Failed to load indicator:", error);
      toast.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIndicatorTasks();
    loadData();
  }, [indicatorId]);

  // 监听mode参数变化
  useEffect(() => {
    setIsEditMode(mode === "edit");
  }, [mode]);

  // 变更检测
  useEffect(() => {
    if (!data || !originalData) return;
    const changed = JSON.stringify(data) !== JSON.stringify(originalData);
    setHasChanges(changed);
  }, [data, originalData]);

  // 字段更新
  const updateField = (field: keyof Indicator, value: any) => {
    if (!data) return;
    setData({ ...data, [field]: value });
  };

  // 保存
  const handleSave = async () => {
    if (!data || !hasChanges) return;

    setSaving(true);
    try {
      const updateData: IndicatorUpdate = {
        indicator_name: data.indicator_name,
        description: data.description,
        data_type: data.data_type,
        enum_values: data.enum_values
      };

      await indicatorService.update(indicatorId, updateData);
      toast.success("保存成功");
      await loadData();
      router.push(`/fraudhunter/indicators/${indicatorId}`);
    } catch (error: any) {
      console.error("Failed to update indicator:", error);
      const detail = error.response?.data?.detail;
      toast.error(detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    if (hasChanges) {
      confirm({
        title: "确认取消",
        description: "确定要取消吗？未保存的更改将丢失",
        variant: "default",
        onConfirm: () => {
          router.push(`/fraudhunter/indicators/${indicatorId}`);
        }
      });
    } else {
      router.push(`/fraudhunter/indicators/${indicatorId}`);
    }
  };

  // 进入编辑模式
  const handleEdit = () => {
    router.push(`/fraudhunter/indicators/${indicatorId}?mode=edit`);
  };

  // 归档
  const handleArchive = () => {
    confirm({
      title: "确认归档",
      description: "确定要归档此指标吗？",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await indicatorService.archive(indicatorId);
          toast.success("归档成功");
          await loadData();
        } catch (error: any) {
          console.error("Failed to archive indicator:", error);
          toast.error(error.response?.data?.detail || "归档失败");
        }
      }
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">指标不存在</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push("/fraudhunter/indicators")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <h1 className="text-2xl font-bold">{data.indicator_name}</h1>
          <Badge>{data.status}</Badge>
        </div>
        <div className="flex gap-2">
          {isEditMode ? (
            <>
              <Button variant="outline" onClick={handleCancel}>
                取消
              </Button>
              <Button onClick={handleSave} disabled={!hasChanges || saving}>
                {saving ? "保存中..." : "保存"}
              </Button>
            </>
          ) : (
            <Button onClick={handleEdit}>编辑</Button>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>指标编码</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {data.indicator_code}
              </div>
            </div>
            <div>
              <Label>状态</Label>
              <div className="mt-1">
                <Badge>{data.status}</Badge>
              </div>
            </div>
          </div>

          <div>
            <Label htmlFor="indicator-name">指标名称</Label>
            {isEditMode ? (
              <Input
                id="indicator-name"
                value={data.indicator_name}
                onChange={(e) => updateField("indicator_name", e.target.value)}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {data.indicator_name}
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="description">描述</Label>
            {isEditMode ? (
              <Textarea
                id="description"
                value={data.description || ""}
                onChange={(e) => updateField("description", e.target.value)}
                rows={3}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded whitespace-pre-wrap">
                {data.description || "暂无描述"}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>指标类型</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                <Badge variant="outline">
                  {data.indicator_type === "offline" ? "离线" : "实时"}
                </Badge>
              </div>
            </div>
            <div>
              <Label htmlFor="object-type">对象类型</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                <Badge variant="outline">
                  {data.object_type === "cust_no" ? "客户号" :
                   data.object_type === "dep_acct_no" ? "存款账号" : "贷款账号"}
                </Badge>
              </div>
              {isEditMode && (
                <p className="text-sm text-muted-foreground mt-1">
                  对象类型不可修改
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>关联指标任务</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {IndicatorTasks.find(g => g.id === data.indicator_task_id)?.task_name ||
                 `指标任务 ${data.indicator_task_id}`}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>当前版本</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {data.current_version}
              </div>
            </div>
            <div>
              <Label>最新版本</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {data.latest_version}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>创建时间</Label>
              <div className="mt-1 p-2 bg-muted rounded text-sm">
                {new Date(data.created_at).toLocaleString()}
              </div>
            </div>
            <div>
              <Label>更新时间</Label>
              <div className="mt-1 p-2 bg-muted rounded text-sm">
                {new Date(data.updated_at).toLocaleString()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据定义 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>数据定义</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="data-type">数据类型</Label>
            {isEditMode ? (
              <Select
                value={data.data_type}
                onValueChange={(value) => {
                  updateField("data_type", value);
                }}
              >
                <SelectTrigger id="data-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="numeric">数值</SelectItem>
                  <SelectItem value="text">文本</SelectItem>
                  <SelectItem value="date">日期</SelectItem>
                </SelectContent>
              </Select>
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {{
                  int: "整数",
                  float: "浮点数",
                  string: "字符串",
                  bool: "布尔",
                  date: "日期",
                  text: "文本",
                  numeric: "数值"
                }[data.data_type] || data.data_type}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 操作区 */}
      {!isEditMode && (
        <Card>
          <CardHeader>
            <CardTitle>操作</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-4">
            <Button variant="destructive" onClick={handleArchive}>
              归档
            </Button>
          </CardContent>
        </Card>
      )}
      <DialogComponent />
    </div>
  );
}
