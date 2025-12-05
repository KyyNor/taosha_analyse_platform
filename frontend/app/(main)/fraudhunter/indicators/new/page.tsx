"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { indicatorService, indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { IndicatorCreate, IndicatorTask } from "@/lib/services/fraudhunterService";

export default function NewIndicatorPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [IndicatorTasks, setIndicatorTasks] = useState<IndicatorTask[]>([]);
  const [formData, setFormData] = useState<IndicatorCreate>({
    indicator_code: "",
    indicator_name: "",
    indicator_type: "offline",
    object_type: "cust_no",
    description: "",
    data_type: "numeric",
    enum_values: "",
    indicator_task_id: 0
  });

  // 加载指标任务列表
  useEffect(() => {
    const loadIndicatorTasks = async () => {
      try {
        const response = await indicatorTaskService.list({});
        setIndicatorTasks(response.items || []);
      } catch (error) {
        console.error("Failed to load indicator tasks:", error);
      }
    };
    loadIndicatorTasks();
  }, []);

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!formData.indicator_code?.trim()) {
      errors.push("指标编码不能为空");
    } else if (formData.indicator_code.length > 64) {
      errors.push("指标编码不能超过64个字符");
    }

    if (!formData.indicator_name?.trim()) {
      errors.push("指标名称不能为空");
    } else if (formData.indicator_name.length > 128) {
      errors.push("指标名称不能超过128个字符");
    }

    if (!formData.indicator_type) {
      errors.push("请选择指标类型");
    }

    if (!formData.object_type) {
      errors.push("请选择对象类型");
    }

    if (!formData.data_type) {
      errors.push("请选择数据类型");
    }

    if (formData.data_type === "enum" && !formData.enum_values?.trim()) {
      errors.push("枚举类型必须提供枚举值");
    }

    if (formData.data_type === "enum" && formData.enum_values) {
      try {
        const parsed = JSON.parse(formData.enum_values);
        if (!Array.isArray(parsed)) {
          errors.push("枚举值必须是JSON数组格式，如：[\"value1\", \"value2\"]");
        }
      } catch (e) {
        errors.push("枚举值必须是有效的JSON数组格式");
      }
    }

    if (!formData.indicator_task_id || formData.indicator_task_id === 0) {
      errors.push("请选择关联的指标任务");
    }

    return errors;
  };

  // 保存处理
  const handleSave = async () => {
    const errors = validateForm();
    if (errors.length > 0) {
      alert("表单验证失败:\n" + errors.join("\n"));
      return;
    }

    setSaving(true);
    try {
      const result = await indicatorService.create(formData);
      alert("指标创建成功");
      router.push(`/fraudhunter/indicators/${result.id}`);
    } catch (error: any) {
      console.error("Failed to create indicator:", error);
      const detail = error.response?.data?.detail;
      alert(detail || "创建失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  // 取消处理
  const handleCancel = () => {
    if (confirm("确定要取消吗？未保存的更改将丢失")) {
      router.push("/fraudhunter/indicators");
    }
  };

  // 字段更新处理
  const updateField = (field: keyof IndicatorCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="outline"
          onClick={() => router.push("/fraudhunter/indicators")}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCancel}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "创建中..." : "创建指标"}
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
            <Label htmlFor="indicator-code">指标编码 *</Label>
            <Input
              id="indicator-code"
              value={formData.indicator_code}
              onChange={(e) => updateField("indicator_code", e.target.value)}
              placeholder="如: login_freq_7d"
              maxLength={64}
            />
            <p className="text-sm text-muted-foreground mt-1">
              唯一标识，1-64个字符
            </p>
          </div>

          <div>
            <Label htmlFor="indicator-name">指标名称 *</Label>
            <Input
              id="indicator-name"
              value={formData.indicator_name}
              onChange={(e) => updateField("indicator_name", e.target.value)}
              placeholder="如: 7天登录频率"
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
              placeholder="描述指标的业务含义和计算逻辑"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="indicator-type">指标类型 *</Label>
              <Select
                value={formData.indicator_type}
                onValueChange={(value) => updateField("indicator_type", value)}
              >
                <SelectTrigger id="indicator-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="offline">离线</SelectItem>
                  <SelectItem value="realtime">实时</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground mt-1">
                离线指标通过批处理计算，实时指标通过流式计算
              </p>
            </div>

            <div>
              <Label htmlFor="object-type">对象类型 *</Label>
              <Select
                value={formData.object_type}
                onValueChange={(value) => updateField("object_type", value)}
              >
                <SelectTrigger id="object-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cust_no">客户号</SelectItem>
                  <SelectItem value="dep_acct_no">存款账号</SelectItem>
                  <SelectItem value="loan_acct_no">贷款账号</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground mt-1">
                指标计算的对象类型
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="indicator-task">关联指标任务 *</Label>
              <Select
                value={String(formData.indicator_task_id)}
                onValueChange={(value) => updateField("indicator_task_id", Number(value))}
              >
                <SelectTrigger id="indicator-task">
                  <SelectValue placeholder="选择指标任务" />
                </SelectTrigger>
                <SelectContent>
                  {IndicatorTasks.map((task) => (
                    <SelectItem key={task.id} value={String(task.id)}>
                      {task.task_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground mt-1">
                指标所属的指标任务
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据定义 */}
      <Card>
        <CardHeader>
          <CardTitle>数据定义</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="data-type">数据类型 *</Label>
            <Select
              value={formData.data_type}
              onValueChange={(value) => {
                updateField("data_type", value);
                // 非枚举类型时清空枚举值
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
            <p className="text-sm text-muted-foreground mt-1">
              指标值的数据类型
            </p>
          </div>

          {formData.data_type === "enum" && (
            <div>
              <Label htmlFor="enum-values">枚举值 *</Label>
              <Textarea
                id="enum-values"
                value={formData.enum_values}
                onChange={(e) => updateField("enum_values", e.target.value)}
                placeholder='["low", "medium", "high"]'
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-sm text-muted-foreground mt-1">
                JSON数组格式，如：["value1", "value2", "value3"]
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
