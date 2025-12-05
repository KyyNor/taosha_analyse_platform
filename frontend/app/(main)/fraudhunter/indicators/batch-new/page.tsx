"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, Trash2, Check, X } from "lucide-react";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  indicatorService,
  indicatorTaskService
} from "@/lib/services/fraudhunterService";
import type {
  IndicatorTask,
  IndicatorBatchCreateItem,
  IndicatorTaskBatchCreate,
  IndicatorTaskCreate
} from "@/lib/services/fraudhunterService";

export default function BatchNewIndicatorPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [taskMode, setTaskMode] = useState<"existing" | "new">("existing");
  const [existingTasks, setExistingTasks] = useState<IndicatorTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<number>(0);

  // 新建任务数据
  const [newTaskData, setNewTaskData] = useState<IndicatorTaskCreate>({
    task_name: "",
    description: "",
    logic_content: "",
    source_tables: ""
  });

  // 批量指标数据
  const [indicators, setIndicators] = useState<IndicatorBatchCreateItem[]>([
    {
      indicator_name: "",
      indicator_type: "offline",
      object_type: "dep_acct_no",
      description: "",
      data_type: "numeric",
      enum_values: ""
    }
  ]);

  // 结果状态
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState<any>(null);

  // 加载现有任务列表
  useEffect(() => {
    const loadTasks = async () => {
      try {
        const response = await indicatorTaskService.list({ page_size: 100 });
        setExistingTasks(response.items || []);
      } catch (error) {
        console.error("Failed to load tasks:", error);
      }
    };
    loadTasks();
  }, []);

  // 添加指标
  const handleAddIndicator = () => {
    if (indicators.length >= 50) {
      alert("最多可添加50个指标");
      return;
    }
    setIndicators([
      ...indicators,
      {
        indicator_name: "",
        indicator_type: "offline",
        object_type: "dep_acct_no",
        description: "",
        data_type: "numeric",
        enum_values: ""
      }
    ]);
  };

  // 删除指标
  const handleRemoveIndicator = (index: number) => {
    if (indicators.length <= 1) {
      alert("至少保留一个指标");
      return;
    }
    setIndicators(indicators.filter((_, i) => i !== index));
  };

  // 更新指标字段
  const updateIndicator = (index: number, field: keyof IndicatorBatchCreateItem, value: any) => {
    const updated = [...indicators];
    updated[index] = { ...updated[index], [field]: value };
    setIndicators(updated);
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证任务
    if (taskMode === "existing") {
      if (!selectedTaskId || selectedTaskId === 0) {
        errors.push("请选择指标任务");
      }
    } else {
      if (!newTaskData.task_name?.trim()) {
        errors.push("新任务名称不能为空");
      }
      if (!newTaskData.logic_content?.trim()) {
        errors.push("新任务SQL内容不能为空");
      }
    }

    // 验证指标
    if (indicators.length === 0) {
      errors.push("至少添加一个指标");
    }

    indicators.forEach((indicator, idx) => {
      if (!indicator.indicator_name?.trim()) {
        errors.push(`第${idx + 1}个指标：名称不能为空`);
      }
      if (indicator.data_type === "enum" && !indicator.enum_values?.trim()) {
        errors.push(`第${idx + 1}个指标：枚举类型必须提供枚举值`);
      }
    });

    return errors;
  };

  // 提交处理
  const handleSubmit = async () => {
    const errors = validateForm();
    if (errors.length > 0) {
      alert("表单验证失败:\n" + errors.join("\n"));
      return;
    }

    setSaving(true);
    try {
      const batchData: IndicatorTaskBatchCreate = {
        indicator_task_id: taskMode === "existing" ? selectedTaskId : undefined,
        new_task: taskMode === "new" ? newTaskData : undefined,
        indicators: indicators
      };

      const response = await indicatorService.batchCreate(batchData);

      setResult(response);
      setShowResult(true);

    } catch (error: any) {
      console.error("Batch create failed:", error);
      alert(error.response?.data?.detail || "批量创建失败，请重试");
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

  // 结果显示页面
  if (showResult && result) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">批量创建结果</h1>
          <Button onClick={() => router.push("/fraudhunter/indicators")}>
            返回指标列表
          </Button>
        </div>

        {/* 概览 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>创建概览</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p><strong>指标任务：</strong>{result.task_name} ({result.task_code})</p>
              <p><strong>总计：</strong>{result.total} 个指标</p>
              <p className="text-green-600"><strong>成功：</strong>{result.success_count} 个</p>
              {result.failed_count > 0 && (
                <p className="text-red-600"><strong>失败：</strong>{result.failed_count} 个</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 详细结果 */}
        <Card>
          <CardHeader>
            <CardTitle>详细结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {result.results.map((item: any, idx: number) => (
                <div
                  key={idx}
                  className={`p-4 rounded-md border ${
                    item.success
                      ? "bg-green-50 border-green-200"
                      : "bg-red-50 border-red-200"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {item.success ? (
                          <Check className="h-5 w-5 text-green-600" />
                        ) : (
                          <X className="h-5 w-5 text-red-600" />
                        )}
                        <span className="font-medium">
                          第 {idx + 1} 个指标
                        </span>
                      </div>
                      {item.success ? (
                        <div className="text-sm text-muted-foreground">
                          <p>编码: {item.indicator?.indicator_code}</p>
                          <p>名称: {item.indicator?.indicator_name}</p>
                        </div>
                      ) : (
                        <p className="text-sm text-red-600">{item.error}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 创建表单页面
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
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? "创建中..." : "批量创建"}
          </Button>
        </div>
      </div>

      {/* 任务选择 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>指标任务</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <RadioGroup value={taskMode} onValueChange={(v) => setTaskMode(v as any)}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="existing" id="existing" />
              <Label htmlFor="existing">使用现有任务</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="new" id="new" />
              <Label htmlFor="new">创建新任务</Label>
            </div>
          </RadioGroup>

          {taskMode === "existing" && (
            <div>
              <Label>选择指标任务 *</Label>
              <Select
                value={String(selectedTaskId)}
                onValueChange={(v) => setSelectedTaskId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择指标任务" />
                </SelectTrigger>
                <SelectContent>
                  {existingTasks.map((task) => (
                    <SelectItem key={task.id} value={String(task.id)}>
                      {task.task_name} ({task.task_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {taskMode === "new" && (
            <div className="space-y-4 p-4 border rounded-md">
              <div>
                <Label>任务名称 *</Label>
                <Input
                  value={newTaskData.task_name}
                  onChange={(e) => setNewTaskData({ ...newTaskData, task_name: e.target.value })}
                  placeholder="如: 登录行为指标任务"
                />
              </div>
              <div>
                <Label>描述</Label>
                <Textarea
                  value={newTaskData.description}
                  onChange={(e) => setNewTaskData({ ...newTaskData, description: e.target.value })}
                  placeholder="描述任务用途"
                  rows={2}
                />
              </div>
              <div>
                <Label>SQL内容 *</Label>
                <Textarea
                  value={newTaskData.logic_content}
                  onChange={(e) => setNewTaskData({ ...newTaskData, logic_content: e.target.value })}
                  placeholder="SELECT account_id, indicator_code, indicator_value, dt FROM ..."
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label>依赖源表</Label>
                <Input
                  value={newTaskData.source_tables}
                  onChange={(e) => setNewTaskData({ ...newTaskData, source_tables: e.target.value })}
                  placeholder="如: user_login,user_session"
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 批量指标 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>批量指标 ({indicators.length}/50)</CardTitle>
            <Button onClick={handleAddIndicator} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              添加指标
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {indicators.map((indicator, idx) => (
            <div key={idx} className="p-4 border rounded-md space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">指标 {idx + 1}</h3>
                {indicators.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveIndicator(idx)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>指标名称 *</Label>
                  <Input
                    value={indicator.indicator_name}
                    onChange={(e) => updateIndicator(idx, "indicator_name", e.target.value)}
                    placeholder="如: 7天登录频率"
                  />
                </div>

                <div>
                  <Label>描述</Label>
                  <Input
                    value={indicator.description}
                    onChange={(e) => updateIndicator(idx, "description", e.target.value)}
                    placeholder="指标描述"
                  />
                </div>

                <div>
                  <Label>指标类型 *</Label>
                  <Select
                    value={indicator.indicator_type}
                    onValueChange={(v) => updateIndicator(idx, "indicator_type", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="offline">离线</SelectItem>
                      <SelectItem value="realtime">实时</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>对象类型 *</Label>
                  <Select
                    value={indicator.object_type}
                    onValueChange={(v) => updateIndicator(idx, "object_type", v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cust_no">客户号</SelectItem>
                      <SelectItem value="dep_acct_no">存款账号</SelectItem>
                      <SelectItem value="loan_acct_no">贷款账号</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>数据类型 *</Label>
                  <Select
                    value={indicator.data_type}
                    onValueChange={(v) => {
                      updateIndicator(idx, "data_type", v);
                      if (v !== "enum") {
                        updateIndicator(idx, "enum_values", "");
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="numeric">数值</SelectItem>
                      <SelectItem value="enum">枚举</SelectItem>
                      <SelectItem value="text">文本</SelectItem>
                      <SelectItem value="boolean">布尔</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {indicator.data_type === "enum" && (
                  <div className="col-span-2">
                    <Label>枚举值 *</Label>
                    <Textarea
                      value={indicator.enum_values}
                      onChange={(e) => updateIndicator(idx, "enum_values", e.target.value)}
                      placeholder='["low", "medium", "high"]'
                      rows={2}
                      className="font-mono text-sm"
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
