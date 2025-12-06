"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileCode, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { riskControlModelService } from "@/lib/services/fraudhunterService";
import { indicatorService } from "@/lib/services/fraudhunterService";
import { modelService } from "@/lib/services/fraudhunter/modelService";
import type { RiskControlModelCreate, ObjectType } from "@/types/fraudhunter/risk-control-model";
import type { RuleConfig, Indicator } from "@/types/fraudhunter/rule";
import { RuleBuilder } from "@/components/fraudhunter/model/RuleBuilder";
import { getObjectTypeLabel } from "@/types/fraudhunter/risk-control-model";

export default function NewRiskControlModelPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [generatingSQL, setGeneratingSQL] = useState(false);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [sqlPreview, setSqlPreview] = useState<string>("");
  const [showSQLPreview, setShowSQLPreview] = useState(false);

  // 表单数据
  const [formData, setFormData] = useState<RiskControlModelCreate>({
    model_code: "",
    model_name: "",
    description: "",
    object_type: "cust_no",
    rule_config: {
      logic: "AND",
      rules: [],
      output: {
        risk_level: "medium",
        risk_score: 50,
        action: "review"
      }
    },
    is_send_alert_message: false,
    alert_message_target: "",
    is_acct_control: false
  });

  // 根据object_type加载指标
  useEffect(() => {
    const loadIndicators = async () => {
      try {
        const response = await indicatorService.list({
          object_type: formData.object_type,
          status: "online",
          page_size: 1000
        });
        // 转换为规则引擎需要的格式
        const transformedIndicators: Indicator[] = (response.items || []).map(item => ({
          indicator_code: item.indicator_code,
          indicator_name: item.indicator_name,
          data_type: item.data_type,
          enum_values: item.enum_values ? item.enum_values.split(',').map(v => v.trim()) : undefined,
          description: item.description
        }));
        setIndicators(transformedIndicators);
      } catch (error) {
        console.error("Failed to load indicators:", error);
      }
    };
    loadIndicators();
  }, [formData.object_type]);

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!formData.model_code?.trim()) {
      errors.push("模型编码不能为空");
    } else if (formData.model_code.length > 64) {
      errors.push("模型编码不能超过64个字符");
    }

    if (!formData.model_name?.trim()) {
      errors.push("模型名称不能为空");
    } else if (formData.model_name.length > 128) {
      errors.push("模型名称不能超过128个字符");
    }

    if (!formData.object_type) {
      errors.push("请选择对象类型");
    }

    if (!formData.rule_config || formData.rule_config.rules.length === 0) {
      errors.push("至少需要配置一条规则");
    }

    if (formData.is_send_alert_message && !formData.alert_message_target?.trim()) {
      errors.push("开启告警消息时，告警目标不能为空");
    }

    return errors;
  };

  // 生成SQL预览
  const handleGenerateSQL = async () => {
    if (!formData.rule_config || formData.rule_config.rules.length === 0) {
      alert("请先配置规则");
      return;
    }

    setGeneratingSQL(true);
    try {
      const result = await modelService.previewSQL(formData.rule_config);
      setSqlPreview(result.sql_expression);
      setShowSQLPreview(true);
    } catch (error: any) {
      console.error("Failed to generate SQL:", error);
      const detail = error.response?.data?.detail;
      if (detail?.errors) {
        alert("SQL生成失败:\n" + detail.errors.join("\n"));
      } else {
        alert(detail?.message || "SQL生成失败");
      }
    } finally {
      setGeneratingSQL(false);
    }
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
      const result = await riskControlModelService.create(formData);
      alert("预警管控模型创建成功");
      router.push(`/fraudhunter/risk-control-models/${result.id}`);
    } catch (error: any) {
      console.error("Failed to create risk control model:", error);
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail?.errors) {
        alert("创建失败:\n" + detail.errors.join("\n"));
      } else {
        alert(detail || "创建失败，请重试");
      }
    } finally {
      setSaving(false);
    }
  };

  // 取消处理
  const handleCancel = () => {
    if (confirm("确定要取消吗？未保存的更改将丢失")) {
      router.push("/fraudhunter/risk-control-models");
    }
  };

  // 字段更新处理
  const updateField = <K extends keyof RiskControlModelCreate>(
    field: K,
    value: RiskControlModelCreate[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // 规则变化处理
  const handleRuleChange = (newRule: RuleConfig) => {
    updateField("rule_config", newRule);
    // 清空SQL预览
    setShowSQLPreview(false);
    setSqlPreview("");
  };

  return (
    <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="outline"
          onClick={() => router.push("/fraudhunter/risk-control-models")}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCancel}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "创建中..." : "创建模型"}
          </Button>
        </div>
      </div>

      <div className="space-y-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="model-code">模型编码 *</Label>
              <Input
                id="model-code"
                value={formData.model_code}
                onChange={(e) => updateField("model_code", e.target.value)}
                placeholder="如: risk_model_001"
                maxLength={64}
              />
              <p className="text-sm text-muted-foreground mt-1">
                唯一标识，1-64个字符
              </p>
            </div>

            <div>
              <Label htmlFor="model-name">模型名称 *</Label>
              <Input
                id="model-name"
                value={formData.model_name}
                onChange={(e) => updateField("model_name", e.target.value)}
                placeholder="如: 高风险客户预警模型"
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
                placeholder="描述模型的业务目的和应用场景"
                rows={3}
              />
            </div>

            <div>
              <Label htmlFor="object-type">对象类型 *</Label>
              <Select
                value={formData.object_type}
                onValueChange={(value: ObjectType) => updateField("object_type", value)}
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
                选择后将加载对应的指标列表
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 规则配置 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>规则配置</CardTitle>
              <Badge variant="outline">
                对象类型: {getObjectTypeLabel(formData.object_type)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <RuleBuilder
              indicators={indicators}
              initialRule={formData.rule_config}
              onChange={handleRuleChange}
            />
          </CardContent>
        </Card>

        {/* SQL预览 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>SQL预览</CardTitle>
              <Button
                variant="outline"
                onClick={handleGenerateSQL}
                disabled={generatingSQL || formData.rule_config.rules.length === 0}
              >
                <FileCode className="h-4 w-4 mr-2" />
                {generatingSQL ? "生成中..." : "生成SQL"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showSQLPreview && sqlPreview ? (
              <pre className="bg-muted p-4 rounded-md overflow-x-auto text-sm">
                {sqlPreview}
              </pre>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>点击"生成SQL"按钮预览离线模型SQL</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 告警配置 */}
        <Card>
          <CardHeader>
            <CardTitle>告警配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="send-alert"
                checked={formData.is_send_alert_message}
                onCheckedChange={(checked) =>
                  updateField("is_send_alert_message", checked as boolean)
                }
              />
              <Label htmlFor="send-alert" className="cursor-pointer">
                发送告警消息
              </Label>
            </div>

            {formData.is_send_alert_message && (
              <div>
                <Label htmlFor="alert-target">告警消息目标 *</Label>
                <Input
                  id="alert-target"
                  value={formData.alert_message_target}
                  onChange={(e) => updateField("alert_message_target", e.target.value)}
                  placeholder="如: admin@example.com"
                  maxLength={256}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  邮箱、手机号或其他告警通道
                </p>
              </div>
            )}

            <div className="flex items-center space-x-2">
              <Checkbox
                id="acct-control"
                checked={formData.is_acct_control}
                onCheckedChange={(checked) =>
                  updateField("is_acct_control", checked as boolean)
                }
              />
              <Label htmlFor="acct-control" className="cursor-pointer">
                账户控制
              </Label>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
