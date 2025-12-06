"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { IndicatorTaskCreate } from "@/lib/services/fraudhunterService";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function NewIndicatorTaskPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const { confirm, DialogComponent } = useConfirmDialog();
  const [formData, setFormData] = useState<IndicatorTaskCreate>({
    task_code: "",
    task_name: "",
    description: "",
    logic_content: "",
    realtime_logic_content: "",
    source_tables: ""
  });

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!formData.task_name?.trim()) {
      errors.push("指标任务名称不能为空");
    } else if (formData.task_name.length > 128) {
      errors.push("指标任务名称不能超过128个字符");
    }

    if (!formData.logic_content?.trim()) {
      errors.push("SQL内容不能为空");
    }

    return errors;
  };

  // 保存处理
  const handleSave = async () => {
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error("表单验证失败: " + errors.join(", "));
      return;
    }

    setSaving(true);
    try {
      const response = await indicatorTaskService.create(formData);

      // 检查响应中的 success 字段
      if (response.success === false) {
        // SQL验证失败或其他业务错误
        const errorMsg = [
          response.message || "创建失败",
          ...(response.errors || [])
        ].filter(Boolean).join(", ");
        toast.error(errorMsg);
        return;
      }

      // 成功
      toast.success("指标任务创建成功");
      if (response.data?.id) {
        router.push(`/fraudhunter/indicator-tasks/${response.data.id}`);
      } else {
        // 如果没有返回 ID，返回列表页
        router.push("/fraudhunter/indicator-tasks");
      }
    } catch (error: any) {
      console.error("Failed to create indicator task:", error);
      // 仅处理网络错误或500错误
      toast.error(error.response?.data?.detail || "创建失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  // 取消处理
  const handleCancel = () => {
    confirm({
      title: "确认取消",
      description: "确定要取消吗？未保存的更改将丢失",
      onConfirm: () => router.push("/fraudhunter/indicator-tasks"),
      variant: "default"
    });
  };

  // 字段更新处理
  const updateField = (field: keyof IndicatorTaskCreate, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <>
      <DialogComponent />
      <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="outline"
          onClick={() => router.push("/fraudhunter/indicator-tasks")}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCancel}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "创建中..." : "创建指标任务"}
          </Button>
        </div>
      </div>

      {/* 基本信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="task-name">指标任务名称 *</Label>
            <Input
              id="task-name"
              value={formData.task_name}
              onChange={(e) => updateField("task_name", e.target.value)}
              placeholder="如: 登录行为指标任务"
              maxLength={128}
            />
            <p className="text-sm text-muted-foreground mt-1">
              显示名称，1-128个字符
            </p>
          </div>

          <div>
            <Label htmlFor="description">描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => updateField("description", e.target.value)}
              placeholder="描述指标任务的用途和业务含义"
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* SQL逻辑 */}
      <Card>
        <CardHeader>
          <CardTitle>SQL加工逻辑</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="logic-content">离线指标SQL *</Label>
            <Textarea
              id="logic-content"
              value={formData.logic_content}
              onChange={(e) => updateField("logic_content", e.target.value)}
              placeholder="SELECT account_id, indicator_code, indicator_value, dt FROM ..."
              rows={15}
              className="font-mono text-sm"
            />
            <p className="text-sm text-muted-foreground mt-1">
              编写离线指标SQL查询逻辑，禁止使用危险操作（DROP、DELETE等）
            </p>
          </div>

          <div>
            <Label htmlFor="realtime-logic-content">实时指标SQL</Label>
            <Textarea
              id="realtime-logic-content"
              value={formData.realtime_logic_content || ""}
              onChange={(e) => updateField("realtime_logic_content", e.target.value)}
              placeholder="SELECT account_id, indicator_code, indicator_value FROM ..."
              rows={15}
              className="font-mono text-sm"
            />
            <p className="text-sm text-muted-foreground mt-1">
              编写实时指标SQL查询逻辑（可选）
            </p>
          </div>

          <div>
            <Label htmlFor="source-tables">依赖源表</Label>
            <Input
              id="source-tables"
              value={formData.source_tables}
              onChange={(e) => updateField("source_tables", e.target.value)}
              placeholder="如: user_login,user_session"
            />
            <p className="text-sm text-muted-foreground mt-1">
              多个表用逗号分隔
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
    </>
  );
}
