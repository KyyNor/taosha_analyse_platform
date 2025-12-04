"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { indicatorGroupService } from "@/lib/services/fraudhunterService";
import type { IndicatorGroup, IndicatorGroupUpdate } from "@/lib/services/fraudhunterService";

export default function IndicatorGroupDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const groupId = Number(params.id);
  const mode = searchParams.get("mode");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === "edit");
  const [data, setData] = useState<IndicatorGroup | null>(null);
  const [originalData, setOriginalData] = useState<IndicatorGroup | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // 试运行对话框状态
  const [dryRunDialogOpen, setDryRunDialogOpen] = useState(false);
  const [dryRunData, setDryRunData] = useState({
    etl_date: new Date().toISOString().split("T")[0],
    sample_size: 100,
    group_version: 1
  });

  // 发布对话框状态
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [publishData, setPublishData] = useState({
    version: 1,
    change_description: ""
  });

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await indicatorGroupService.get(groupId);
      setData(result);
      setOriginalData(JSON.parse(JSON.stringify(result)));
    } catch (error) {
      console.error("Failed to load indicator group:", error);
      alert("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [groupId]);

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
  const updateField = (field: keyof IndicatorGroup, value: any) => {
    if (!data) return;
    setData({ ...data, [field]: value });
  };

  // 保存
  const handleSave = async () => {
    if (!data || !hasChanges) return;

    // 验证
    if (data.status !== "draft" && data.logic_content !== originalData?.logic_content) {
      alert("只有草稿状态的指标组才允许修改SQL内容");
      return;
    }

    setSaving(true);
    try {
      const updateData: IndicatorGroupUpdate = {
        group_name: data.group_name,
        description: data.description,
        logic_content: data.logic_content,
        source_tables: data.source_tables,
        output_table: data.output_table
      };

      await indicatorGroupService.update(groupId, updateData);
      alert("保存成功");
      await loadData();
      router.push(`/fraudhunter/indicator-groups/${groupId}`);
    } catch (error: any) {
      console.error("Failed to update indicator group:", error);
      const detail = error.response?.data?.detail;
      if (typeof detail === "object" && detail.message) {
        alert([detail.message, ...(detail.errors || [])].join("\n"));
      } else {
        alert(detail || "保存失败");
      }
    } finally {
      setSaving(false);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    if (hasChanges && !confirm("确定要取消吗？未保存的更改将丢失")) {
      return;
    }
    router.push(`/fraudhunter/indicator-groups/${groupId}`);
  };

  // 进入编辑模式
  const handleEdit = () => {
    router.push(`/fraudhunter/indicator-groups/${groupId}?mode=edit`);
  };

  // 试运行
  const handleDryRun = async () => {
    try {
      const result = await indicatorGroupService.dryRun(groupId, dryRunData);
      alert(`试运行任务已提交\n任务ID: ${result.task_id}\n请到任务列表查看进度`);
      setDryRunDialogOpen(false);
    } catch (error: any) {
      console.error("Failed to start dry run:", error);
      alert(error.response?.data?.detail || "试运行提交失败");
    }
  };

  // 发布
  const handlePublish = async () => {
    try {
      await indicatorGroupService.publish(groupId, publishData);
      alert("发布成功");
      setPublishDialogOpen(false);
      await loadData();
    } catch (error: any) {
      console.error("Failed to publish indicator group:", error);
      alert(error.response?.data?.detail || "发布失败");
    }
  };

  // 归档
  const handleArchive = async () => {
    if (!confirm("确定要归档此指标组吗？")) return;

    try {
      await indicatorGroupService.archive(groupId);
      alert("归档成功");
      await loadData();
    } catch (error: any) {
      console.error("Failed to archive indicator group:", error);
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
        <div className="text-center">指标组不存在</div>
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
            onClick={() => router.push("/fraudhunter/indicator-groups")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <h1 className="text-2xl font-bold">{data.group_name}</h1>
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
              <Label>指标组编码</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {data.group_code}
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
            <Label htmlFor="group-name">指标组名称</Label>
            {isEditMode ? (
              <Input
                id="group-name"
                value={data.group_name}
                onChange={(e) => updateField("group_name", e.target.value)}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {data.group_name}
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

      {/* SQL逻辑 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>SQL加工逻辑</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="logic-content">SQL内容</Label>
            {isEditMode && data.status === "draft" ? (
              <Textarea
                id="logic-content"
                value={data.logic_content}
                onChange={(e) => updateField("logic_content", e.target.value)}
                rows={15}
                className="font-mono text-sm"
              />
            ) : (
              <div className="mt-1 p-3 bg-muted rounded font-mono text-sm whitespace-pre-wrap">
                {data.logic_content}
              </div>
            )}
            {isEditMode && data.status !== "draft" && (
              <p className="text-sm text-destructive mt-1">
                只有草稿状态才允许修改SQL内容
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="source-tables">依赖源表</Label>
            {isEditMode ? (
              <Input
                id="source-tables"
                value={data.source_tables || ""}
                onChange={(e) => updateField("source_tables", e.target.value)}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {data.source_tables || "无"}
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="output-table">输出表名</Label>
            {isEditMode ? (
              <Input
                id="output-table"
                value={data.output_table || ""}
                onChange={(e) => updateField("output_table", e.target.value)}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {data.output_table}
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
            <Button onClick={() => setDryRunDialogOpen(true)}>
              试运行
            </Button>
            <Button onClick={() => setPublishDialogOpen(true)}>
              发布版本
            </Button>
            <Button variant="destructive" onClick={handleArchive}>
              归档
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 试运行对话框 */}
      <Dialog open={dryRunDialogOpen} onOpenChange={setDryRunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>指标组试运行</DialogTitle>
            <DialogDescription>
              提交异步任务进行试运行，可在任务列表查看进度
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="etl-date">ETL日期 *</Label>
              <Input
                id="etl-date"
                type="date"
                value={dryRunData.etl_date}
                onChange={(e) =>
                  setDryRunData({ ...dryRunData, etl_date: e.target.value })
                }
              />
            </div>
            <div>
              <Label htmlFor="sample-size">样本大小</Label>
              <Input
                id="sample-size"
                type="number"
                value={dryRunData.sample_size}
                onChange={(e) =>
                  setDryRunData({
                    ...dryRunData,
                    sample_size: Number(e.target.value)
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="group-version">指标组版本</Label>
              <Input
                id="group-version"
                type="number"
                value={dryRunData.group_version}
                onChange={(e) =>
                  setDryRunData({
                    ...dryRunData,
                    group_version: Number(e.target.value)
                  })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDryRunDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleDryRun}>开始试运行</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 发布对话框 */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>发布指标组</DialogTitle>
            <DialogDescription>
              将指定版本的指标组发布到生产环境
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
