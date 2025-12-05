"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, Trash2, Check, X, ChevronDown, ChevronRight } from "lucide-react";
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
import { indicatorService } from "@/lib/services/fraudhunterService";
import type {
  IndicatorCreate,
  IndicatorTaskCreate,
  IndicatorBatchCreateItem,
  TaskPreExecuteResponse
} from "@/lib/services/fraudhunterService";

interface CreatedIndicator {
  id: number;
  indicator_code: string;
  indicator_name: string;
  indicator_type: string;
  object_type: string;
}

export default function BatchNewIndicatorPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [isCreating, setIsCreating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // 步骤1：指标配置
  const [indicatorType, setIndicatorType] = useState("offline");
  const [objectType, setObjectType] = useState("dep_acct_no");
  const [indicators, setIndicators] = useState<IndicatorBatchCreateItem[]>([
    {
      indicator_name: "",
      description: "",
      data_type: "numeric",
      enum_values: ""
    }
  ]);

  // 步骤2：已创建的指标
  const [createdIndicators, setCreatedIndicators] = useState<CreatedIndicator[]>([]);
  const [createResults, setCreateResults] = useState<any[]>([]);

  // 步骤3：任务配置
  const [taskData, setTaskData] = useState<IndicatorTaskCreate>({
    task_name: "",
    description: "",
    logic_content: "",
    source_tables: ""
  });

  // 步骤3：预执行验证
  const [etlDate, setEtlDate] = useState("");
  const [validationResult, setValidationResult] = useState<any>(null);

  // 最终结果
  const [finalResult, setFinalResult] = useState<any>(null);

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

  // 步骤1表单验证
  const validateStep1 = () => {
    const errors: string[] = [];

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

  // 步骤3表单验证
  const validateStep3 = () => {
    const errors: string[] = [];

    if (!taskData.task_name?.trim()) {
      errors.push("任务名称不能为空");
    }
    if (!taskData.logic_content?.trim()) {
      errors.push("SQL内容不能为空");
    }

    return errors;
  };

  // 第一步：创建指标
  const handleCreateIndicators = async () => {
    const errors = validateStep1();
    if (errors.length > 0) {
      alert("表单验证失败:\n" + errors.join("\n"));
      return;
    }

    setIsCreating(true);
    const newCreatedIndicators: CreatedIndicator[] = [];
    const newResults: any[] = [];

    try {
      // 逐个创建指标（临时关联到任务ID=0）
      for (let idx = 0; idx < indicators.length; idx++) {
        const indicatorItem = indicators[idx];

        try {
          const indicatorData: IndicatorCreate = {
            indicator_code: undefined, // 自动生成
            indicator_name: indicatorItem.indicator_name,
            indicator_type: indicatorType,
            object_type: objectType,
            description: indicatorItem.description,
            data_type: indicatorItem.data_type,
            enum_values: indicatorItem.enum_values,
            indicator_task_id: undefined // 不关联任务，后续会关联
          };

          const response = await indicatorService.create(indicatorData);

          const createdIndicator: CreatedIndicator = {
            id: response.id,
            indicator_code: response.indicator_code,
            indicator_name: response.indicator_name,
            indicator_type: response.indicator_type,
            object_type: response.object_type
          };

          newCreatedIndicators.push(createdIndicator);
          newResults.push({
            index: idx,
            success: true,
            indicator: createdIndicator,
            error: null
          });

        } catch (error: any) {
          newResults.push({
            index: idx,
            success: false,
            indicator: null,
            error: error.response?.data?.detail || "创建失败"
          });
        }
      }

      setCreatedIndicators(newCreatedIndicators);
      setCreateResults(newResults);
      setCurrentStep(2);

    } catch (error: any) {
      console.error("Batch create indicators failed:", error);
      alert("批量创建指标失败，请重试");
    } finally {
      setIsCreating(false);
    }
  };

  // 第二步：返回修改指标
  const handleBackToStep1 = () => {
    setCurrentStep(1);
    setCreatedIndicators([]);
    setCreateResults([]);
  };

  // 第三步：预执行验证
  const handleValidateTask = async () => {
    const errors = validateStep3();
    if (errors.length > 0) {
      alert("表单验证失败:\n" + errors.join("\n"));
      return;
    }

    setIsValidating(true);
    try {
      const indicatorIds = createdIndicators.map(ind => ind.id);
      const result: TaskPreExecuteResponse = await indicatorService.validateTaskBeforeCreate(
        taskData,
        indicatorIds,
        etlDate || undefined
      );

      setValidationResult(result);

      if (result.success) {
        setCurrentStep(4); // 验证通过，进入第4步创建任务
      } else {
        alert("预执行验证失败: " + result.message);
      }

    } catch (error: any) {
      console.error("Task validation failed:", error);
      alert(error.response?.data?.detail || "预执行验证失败，请重试");
    } finally {
      setIsValidating(false);
    }
  };

  // 第四步：创建任务
  const handleCreateTask = async () => {
    const errors = validateStep3();
    if (errors.length > 0) {
      alert("表单验证失败:\n" + errors.join("\n"));
      return;
    }

    setIsCreating(true);
    try {
      const indicatorIds = createdIndicators.map(ind => ind.id);
      const result = await indicatorService.createTaskWithIndicators(taskData, indicatorIds);

      setFinalResult(result);
      setCurrentStep(4); // 修改为第4步

    } catch (error: any) {
      console.error("Create task failed:", error);
      alert(error.response?.data?.detail || "创建任务失败，请重试");
    } finally {
      setIsCreating(false);
    }
  };

  // 完成流程
  const handleFinish = () => {
    router.push("/fraudhunter/indicators");
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

        {/* 步骤指示器 */}
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${currentStep >= 1 ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 1 ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>1</div>
            <span>创建指标</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <div className={`flex items-center gap-2 ${currentStep >= 2 ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 2 ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>2</div>
            <span>确认指标</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <div className={`flex items-center gap-2 ${currentStep >= 3 ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 3 ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>3</div>
            <span>验证任务</span>
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <div className={`flex items-center gap-2 ${currentStep >= 4 ? "text-blue-600" : "text-gray-400"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 4 ? "bg-blue-600 text-white" : "bg-gray-200"
            }`}>4</div>
            <span>创建任务</span>
          </div>
        </div>
      </div>

      {/* 步骤1：配置和创建指标 */}
      {currentStep === 1 && (
        <>
          {/* 公共设置 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>公共设置（所有指标共享）</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>指标类型 *</Label>
                  <Select
                    value={indicatorType}
                    onValueChange={setIndicatorType}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="offline">离线</SelectItem>
                      <SelectItem value="realtime">实时</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground mt-1">
                    所有指标将使用相同的类型
                  </p>
                </div>

                <div>
                  <Label>对象类型 *</Label>
                  <Select
                    value={objectType}
                    onValueChange={setObjectType}
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
                  <p className="text-sm text-muted-foreground mt-1">
                    所有指标将使用相同的对象类型
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 批量指标配置 */}
          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>指标配置 ({indicators.length}/50)</CardTitle>
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

          {/* 创建按钮 */}
          <div className="flex justify-end">
            <Button
              onClick={handleCreateIndicators}
              disabled={isCreating}
              size="lg"
            >
              {isCreating ? "创建中..." : "创建指标"}
            </Button>
          </div>
        </>
      )}

      {/* 步骤2：显示创建结果 */}
      {currentStep === 2 && (
        <>
          {/* 创建结果概览 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>指标创建结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p><strong>总计：</strong>{indicators.length} 个指标</p>
                <p className="text-green-600"><strong>成功：</strong>{createdIndicators.length} 个</p>
                {createResults.some(r => !r.success) && (
                  <p className="text-red-600"><strong>失败：</strong>{createResults.filter(r => !r.success).length} 个</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 成功创建的指标ID列表 */}
          {createdIndicators.length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>成功创建的指标</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {createdIndicators.map((indicator, idx) => (
                    <div key={idx} className="p-4 bg-green-50 border border-green-200 rounded-md">
                      <div className="flex items-center gap-2 mb-2">
                        <Check className="h-5 w-5 text-green-600" />
                        <span className="font-medium">指标 {idx + 1}</span>
                      </div>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p><strong>ID:</strong> {indicator.id}</p>
                        <p><strong>编码:</strong> {indicator.indicator_code}</p>
                        <p><strong>名称:</strong> {indicator.indicator_name}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 复制所有ID */}
                <div className="mt-4 p-4 bg-gray-50 rounded-md">
                  <Label className="text-sm font-medium">所有指标ID（复制到任务SQL中使用）：</Label>
                  <div className="mt-2 p-3 bg-white border rounded-md font-mono text-sm">
                    {createdIndicators.map(ind => ind.id).join(", ")}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 失败的指标 */}
          {createResults.some(r => !r.success) && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>创建失败的指标</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {createResults
                    .filter(r => !r.success)
                    .map((result, idx) => (
                      <div key={idx} className="p-4 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-center gap-2 mb-2">
                          <X className="h-5 w-5 text-red-600" />
                          <span className="font-medium">指标 {result.index + 1}</span>
                        </div>
                        <p className="text-sm text-red-600">{result.error}</p>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={handleBackToStep1}>
              返回修改
            </Button>
            <Button
              onClick={() => setCurrentStep(3)}
              disabled={createdIndicators.length === 0}
            >
              配置任务
            </Button>
          </div>
        </>
      )}

      {/* 步骤3：配置和验证任务 */}
      {currentStep === 3 && (
        <>
          {/* 任务配置 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>指标任务设置</CardTitle>
              <p className="text-sm text-muted-foreground">
                配置SQL任务逻辑，系统将验证输出字段是否包含 target_id、etl_date 和所有指标字段
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>任务名称 *</Label>
                <Input
                  value={taskData.task_name}
                  onChange={(e) => setTaskData({ ...taskData, task_name: e.target.value })}
                  placeholder="如: 登录行为指标任务"
                />
              </div>
              <div>
                <Label>描述</Label>
                <Textarea
                  value={taskData.description}
                  onChange={(e) => setTaskData({ ...taskData, description: e.target.value })}
                  placeholder="描述任务用途"
                  rows={2}
                />
              </div>
              <div>
                <Label>SQL内容 *</Label>
                <Textarea
                  value={taskData.logic_content}
                  onChange={(e) => setTaskData({ ...taskData, logic_content: e.target.value })}
                  placeholder={`SELECT target_id, etl_date, ${createdIndicators.map(ind => ind.indicator_code).join(', ')} FROM your_table\nWHERE dt = '${date}' -- ${date} 会被替换为实际日期`}
                  rows={8}
                  className="font-mono text-sm"
                />
                <p className="text-sm text-muted-foreground mt-1">
                  提示：SQL中可以使用 {'${date}'} 变量，系统会自动替换为实际ETL日期
                </p>
              </div>
              <div>
                <Label>ETL日期（可选，默认为昨天）</Label>
                <Input
                  type="date"
                  value={etlDate}
                  onChange={(e) => setEtlDate(e.target.value)}
                  placeholder="留空使用昨天的日期"
                />
                <p className="text-sm text-muted-foreground mt-1">
                  验证时使用的日期，留空则默认为昨天
                </p>
              </div>
              <div>
                <Label>依赖源表</Label>
                <Input
                  value={taskData.source_tables}
                  onChange={(e) => setTaskData({ ...taskData, source_tables: e.target.value })}
                  placeholder="如: user_login,user_session"
                />
              </div>
            </CardContent>
          </Card>

          {/* 已关联的指标 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>已关联的指标</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                将关联到这个任务的指标列表：
              </p>
              <div className="space-y-2">
                {createdIndicators.map((indicator, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 rounded-md">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-medium">ID: {indicator.id}</span>
                        <span className="mx-2">·</span>
                        <span>{indicator.indicator_name}</span>
                        <span className="mx-2">·</span>
                        <span className="text-muted-foreground">{indicator.indicator_code}</span>
                      </div>
                      <Check className="h-4 w-4 text-green-600" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 验证结果 */}
          {validationResult && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className={validationResult.success ? "text-green-600" : "text-red-600"}>
                  预执行验证结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className={`p-4 rounded-md ${validationResult.success ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                    <p className={validationResult.success ? "text-green-700" : "text-red-700"}>
                      {validationResult.message}
                    </p>
                  </div>

                  {validationResult.validation_details && (
                    <div>
                      <h4 className="font-medium mb-2">字段验证详情：</h4>
                      <div className="space-y-2 text-sm">
                        <div><strong>必需字段：</strong> {validationResult.validation_details.required_fields.join(", ")}</div>
                        <div><strong>实际字段：</strong> {validationResult.validation_details.actual_fields.join(", ")}</div>
                        {validationResult.validation_details.missing_fields.length > 0 && (
                          <div className="text-red-600"><strong>缺失字段：</strong> {validationResult.validation_details.missing_fields.join(", ")}</div>
                        )}
                        {validationResult.validation_details.extra_fields.length > 0 && (
                          <div className="text-orange-600"><strong>多余字段：</strong> {validationResult.validation_details.extra_fields.join(", ")}</div>
                        )}
                      </div>
                    </div>
                  )}

                  {validationResult.sample_results && (
                    <div>
                      <h4 className="font-medium mb-2">样本数据（前3条）：</h4>
                      <div className="bg-gray-50 p-3 rounded-md">
                        <pre className="text-xs overflow-x-auto">
                          {JSON.stringify(validationResult.sample_results.slice(0, 3), null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setCurrentStep(2)}>
              返回上一步
            </Button>
            <div className="flex gap-2">
              {validationResult?.success && (
                <Button
                  onClick={handleCreateTask}
                  disabled={isCreating}
                  size="lg"
                >
                  {isCreating ? "创建中..." : "创建任务"}
                </Button>
              )}
              <Button
                onClick={handleValidateTask}
                disabled={isValidating}
                variant={validationResult?.success ? "outline" : "default"}
                size="lg"
              >
                {isValidating ? "验证中..." : "预执行验证"}
              </Button>
            </div>
          </div>
        </>
      )}

      {/* 步骤4：任务创建成功 */}
      {currentStep === 4 && finalResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">任务创建成功！</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <p>任务编码: {finalResult.task_code}</p>
                <p>任务名称: {finalResult.task_name}</p>
                <p>关联指标数量: {finalResult.indicator_count}</p>
                <p>预执行验证: 已通过</p>
              </div>
              <div className="mt-6">
                <Button onClick={handleFinish} className="w-full">
                  完成
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 最终结果（兼容旧版本） */}
      {finalResult && currentStep !== 4 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">创建成功！</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <p>任务编码: {finalResult.task_code}</p>
                <p>关联指标数量: {finalResult.indicator_ids.length}</p>
              </div>
              <div className="mt-6">
                <Button onClick={handleFinish} className="w-full">
                  完成
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}