"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { indicatorService, indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { Indicator, IndicatorUpdate, IndicatorTask, PublishRequest } from "@/lib/services/fraudhunterService";

export default function IndicatorDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const indicatorId = Number(params.id);
  const mode = searchParams.get("mode");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === "edit");
  const [data, setData] = useState<Indicator | null>(null);
  const [originalData, setOriginalData] = useState<Indicator | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [IndicatorTasks, setIndicatorTasks] = useState<IndicatorTask[]>([]);

  // 发布对话框状态
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [publishData, setPublishData] = useState<PublishRequest>({
    version: 1,
    change_description: ""
  });

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
      alert("加载失败");
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

    // 验证枚举值
    if (data.data_type === "enum" && data.enum_values) {
      try {
        const parsed = JSON.parse(data.enum_values);
        if (!Array.isArray(parsed)) {
          alert("枚举值必须是JSON数组格式");
          return;
        }
      } catch (e) {
        alert("枚举值必须是有效的JSON格式");
        return;
      }
    }

    setSaving(true);
    try {
      const updateData: IndicatorUpdate = {
        indicator_name: data.indicator_name,
        description: data.description,
        data_type: data.data_type,
        enum_values: data.enum_values
      };

      await indicatorService.update(indicatorId, updateData);
      alert("保存成功");
      await loadData();
      router.push(`/fraudhunter/indicators/${indicatorId}`);
    } catch (error: any) {
      console.error("Failed to update indicator:", error);
      const detail = error.response?.data?.detail;
      alert(detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    if (hasChanges && !confirm("确定要取消吗？未保存的更改将丢失")) {
      return;
    }
    router.push(`/fraudhunter/indicators/${indicatorId}`);
  };

  // 进入编辑模式
  const handleEdit = () => {
    router.push(`/fraudhunter/indicators/${indicatorId}?mode=edit`);
  };

  // 发布
  const handlePublish = async () => {
    try {
      await indicatorService.publish(indicatorId, publishData);
      alert("发布成功");
      setPublishDialogOpen(false);
      await loadData();
    } catch (error: any) {
      console.error("Failed to publish indicator:", error);
      alert(error.response?.data?.detail || "发布失败");
    }
  };

  // 归档
  const handleArchive = async () => {
    if (!confirm("确定要归档此指标吗？")) return;

    try {
      await indicatorService.archive(indicatorId);
      alert("归档成功");
      await loadData();
    } catch (error: any) {
      console.error("Failed to archive indicator:", error);
      alert(error.response?.data?.detail || "归档失败");
    }
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
              {isEditMode ? (
                <Select
                  value={data.object_type}
                  onValueChange={(value) => updateField("object_type", value)}
                >
                  <SelectTrigger id="object-type" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cust_no">客户号</SelectItem>
                    <SelectItem value="dep_acct_no">存款账号</SelectItem>
                    <SelectItem value="loan_acct_no">贷款账号</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <div className="mt-1 p-2 bg-muted rounded">
                  <Badge variant="outline">
                    {data.object_type === "cust_no" ? "客户号" :
                     data.object_type === "dep_acct_no" ? "存款账号" : "贷款账号"}
                  </Badge>
                </div>
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
                  if (value !== "enum") {
                    updateField("enum_values", "");
                  }
                }}
              >
                <SelectTrigger id="data-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="numeric">数值</SelectItem>
                  <SelectItem value="enum">枚举</SelectItem>
                  <SelectItem value="text">文本</SelectItem>
                  <SelectItem value="boolean">布尔</SelectItem>
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
                  numeric: "数值",
                  enum: "枚举",
                  boolean: "布尔"
                }[data.data_type] || data.data_type}
              </div>
            )}
          </div>

          {data.data_type === "enum" && (
            <div>
              <Label htmlFor="enum-values">枚举值</Label>
              {isEditMode ? (
                <Textarea
                  id="enum-values"
                  value={data.enum_values || ""}
                  onChange={(e) => updateField("enum_values", e.target.value)}
                  rows={4}
                  className="font-mono text-sm"
                  placeholder='["value1", "value2", "value3"]'
                />
              ) : (
                <div className="mt-1 p-3 bg-muted rounded font-mono text-sm whitespace-pre-wrap">
                  {data.enum_values || "未设置"}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 操作区 */}
      {!isEditMode && (
        <Card>
          <CardHeader>
            <CardTitle>操作</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-4">
            <Button onClick={() => setPublishDialogOpen(true)}>
              发布版本
            </Button>
            <Button variant="destructive" onClick={handleArchive}>
              归档
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 发布对话框 */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>发布指标</DialogTitle>
            <DialogDescription>
              将指定版本的指标发布到生产环境
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="publish-version">版本号 *</Label>
              <Input
                id="publish-version"
                type="number"
                value={publishData.version}
                onChange={(e) =>
                  setPublishData({
                    ...publishData,
                    version: Number(e.target.value)
                  })
                }
                min={1}
                max={data.latest_version}
              />
              <p className="text-sm text-muted-foreground mt-1">
                可发布版本: 1 - {data.latest_version}
              </p>
            </div>
            <div>
              <Label htmlFor="change-description">变更说明</Label>
              <Textarea
                id="change-description"
                value={publishData.change_description}
                onChange={(e) =>
                  setPublishData({
                    ...publishData,
                    change_description: e.target.value
                  })
                }
                rows={3}
                placeholder="描述此次发布的主要变更"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPublishDialogOpen(false)}
            >
              取消
            </Button>
            <Button onClick={handlePublish}>发布</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
