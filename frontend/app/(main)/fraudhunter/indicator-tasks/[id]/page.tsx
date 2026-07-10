"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, GitCompare } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { IndicatorTask, IndicatorTaskUpdate } from "@/lib/services/fraudhunterService";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { VersionDiffDialog } from "@/components/fraudhunter/indicator/VersionDiffDialog";

export default function IndicatorTaskDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const taskId = Number(params?.id || 0);
  const mode = searchParams?.get("mode")||'view';
  const { confirm, DialogComponent } = useConfirmDialog();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === "edit");
  const [data, setData] = useState<IndicatorTask | null>(null);
  const [originalData, setOriginalData] = useState<IndicatorTask | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // 试运行对话框状态
  const [dryRunDialogOpen, setDryRunDialogOpen] = useState(false);
  // 版本对比对话框状态
  const [versionDiffOpen, setVersionDiffOpen] = useState(false);
  const [dryRunData, setDryRunData] = useState({
    etl_date: new Date().toISOString().split("T")[0],
    sample_size: 100,
    task_version: 1
  });


  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await indicatorTaskService.get(taskId);
      setData(result);
      setOriginalData(JSON.parse(JSON.stringify(result)));
    } catch (error) {
      console.error("Failed to load indicator task:", error);
      toast.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [taskId]);

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
  const updateField = (field: keyof IndicatorTask, value: any) => {
    if (!data) return;
    setData({ ...data, [field]: value });
  };

  // 保存
  const handleSave = async () => {
    if (!data || !hasChanges) return;

    setSaving(true);
    try {
      const updateData: IndicatorTaskUpdate = {
        task_name: data.task_name,
        description: data.description,
        logic_content: data.logic_content,
        realtime_logic_content: data.realtime_logic_content,
        source_tables: data.source_tables
      };

      const response = await indicatorTaskService.update(taskId, updateData);

      // 检查响应中的 success 字段
      if (response.success === false) {
        // SQL验证失败或其他业务错误
        const errorMsg = [
          response.message || "保存失败",
          ...(response.errors || [])
        ].filter(Boolean).join(", ");
        toast.error(errorMsg);
        return;
      }

      // 成功
      toast.success("保存成功");
      await loadData();
      router.push(`/fraudhunter/indicator-tasks/${taskId}`);
    } catch (error: any) {
      console.error("Failed to update indicator task:", error);
      // 仅处理网络错误或500错误
      toast.error(error.response?.data?.detail || "保存失败，请重试");
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
        onConfirm: () => router.push(`/fraudhunter/indicator-tasks/${taskId}`),
        variant: "default"
      });
    } else {
      router.push(`/fraudhunter/indicator-tasks/${taskId}`);
    }
  };

  // 进入编辑模式
  const handleEdit = () => {
    router.push(`/fraudhunter/indicator-tasks/${taskId}?mode=edit`);
  };

  // 试运行
  const handleDryRun = async () => {
    try {
      const result = await indicatorTaskService.dryRun(taskId, dryRunData);
      toast.info(`试运行任务已提交, 任务ID: ${result.task_id}, 请到任务列表查看进度`);
      setDryRunDialogOpen(false);
    } catch (error: any) {
      console.error("Failed to start dry run:", error);
      toast.error(error.response?.data?.detail || "试运行提交失败");
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
        <div className="text-center">指标任务不存在</div>
      </div>
    );
  }

  return (
    <>
      <DialogComponent />
      <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push("/fraudhunter/indicator-tasks")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <h1 className="text-2xl font-bold">{data.task_name}</h1>
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
              <Label>指标任务编码</Label>
              <div className="mt-1 p-2 bg-muted rounded">
                {data.task_code}
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
            <Label htmlFor="task-name">指标任务名称</Label>
            {isEditMode ? (
              <Input
                id="task-name"
                value={data.task_name}
                onChange={(e) => updateField("task_name", e.target.value)}
              />
            ) : (
              <div className="mt-1 p-2 bg-muted rounded">
                {data.task_name}
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

          <div>
            <Label>对象类型</Label>
            <div className="mt-1 p-2 bg-muted rounded">
              {data.object_type === "cust_no" && "客户号"}
              {data.object_type === "dep_acct_no" && "存款账号"}
              {data.object_type === "loan_acct_no" && "贷款账号"}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              对象类型创建后不可修改
            </p>
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
          <div className="flex items-center justify-between">
            <CardTitle>SQL加工逻辑</CardTitle>
            {!isEditMode && data && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setVersionDiffOpen(true)}
                disabled={data.latest_version <= 1}
                title={data.latest_version <= 1 ? "仅有一个版本，无法对比" : "对比当前版本与历史版本"}
              >
                <GitCompare className="h-4 w-4 mr-1" />
                版本对比
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="logic-content">离线指标SQL</Label>
            {isEditMode ? (
              <>
                <Textarea
                  id="logic-content"
                  value={data.logic_content}
                  onChange={(e) => updateField("logic_content", e.target.value)}
                  rows={15}
                  className="font-mono text-sm"
                />
              </>
            ) : (
              <CodeBlock code={data.logic_content} language="sql" />
            )}
          </div>

          <div>
            <Label htmlFor="realtime-logic-content">实时指标SQL</Label>
            {isEditMode ? (
              <>
                <Textarea
                  id="realtime-logic-content"
                  value={data.realtime_logic_content || ""}
                  onChange={(e) => updateField("realtime_logic_content", e.target.value)}
                  rows={15}
                  className="font-mono text-sm"
                />
              </>
            ) : (
              data.realtime_logic_content ? (
                <CodeBlock code={data.realtime_logic_content} language="sql" />
              ) : (
                <div className="mt-1 p-3 bg-muted rounded font-mono text-sm">
                  未配置
                </div>
              )
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
          </CardContent>
        </Card>
      )}

      {/* 试运行对话框 */}
      <Dialog open={dryRunDialogOpen} onOpenChange={setDryRunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>指标任务试运行</DialogTitle>
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
              <Label htmlFor="task-version">指标任务版本</Label>
              <Input
                id="task-version"
                type="number"
                value={dryRunData.task_version}
                onChange={(e) =>
                  setDryRunData({
                    ...dryRunData,
                    task_version: Number(e.target.value)
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

      {/* 版本对比对话框 */}
      {data && (
        <VersionDiffDialog
          open={versionDiffOpen}
          onOpenChange={setVersionDiffOpen}
          taskId={taskId}
          latestVersion={data.latest_version}
        />
      )}
    </div>
    </>
  );
}
