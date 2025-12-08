"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { toast } from 'sonner';
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
import { riskControlModelService } from "@/lib/services/fraudhunterService";
import { indicatorService } from "@/lib/services/fraudhunterService";
import type { RiskControlModelCreate, ObjectType } from "@/types/fraudhunter/risk-control-model";
import type { RuleConfig, Indicator } from "@/types/fraudhunter/rule";
import { RuleBuilder } from "@/components/fraudhunter/model/RuleBuilder";
import { RuleImportExport } from "@/components/fraudhunter/model/RuleImportExport";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function NewRiskControlModelPage() {
  const router = useRouter();
  const { confirm, DialogComponent } = useConfirmDialog();
  const [saving, setSaving] = useState(false);
  const [indicators, setIndicators] = useState<Indicator[]>([]);

  // 表单数据
  const [formData, setFormData] = useState<RiskControlModelCreate>({
    model_code: "",
    model_name: "",
    description: "",
    rule_config: {
      logic: "AND",
      rules: []
    },
    is_send_alert_message: false,
    alert_message_target: "",
    is_acct_control: false
  });

  // 加载所有上线的指标（不按object_type筛选）
  useEffect(() => {
    const loadIndicators = async () => {
      try {
        const response = await indicatorService.list({
          status: "online",
          query_type: "all"
        });
        // 转换为规则引擎需要的格式，包含object_type
        const transformedIndicators: Indicator[] = (response.items || []).map(item => ({
          indicator_code: item.indicator_code,
          indicator_name: item.indicator_name,
          data_type: item.data_type,
          object_type: item.object_type,
          enum_values: item.enum_values ? item.enum_values.split(',').map(v => v.trim()) : undefined,
          description: item.description
        }));
        setIndicators(transformedIndicators);
      } catch (error) {
        console.error("Failed to load indicators:", error);
      }
    };
    loadIndicators();
  }, []);

  // 从规则中提取所有指标编码
  const extractIndicatorCodes = (rules: any[]): string[] => {
    const codes: string[] = [];
    for (const rule of rules) {
      if (rule.type === 'condition' && rule.indicator) {
        codes.push(rule.indicator);
      } else if (rule.type === 'group' && rule.rules) {
        codes.push(...extractIndicatorCodes(rule.rules));
      }
    }
    return codes;
  };

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

    if (!formData.rule_config || formData.rule_config.rules.length === 0) {
      errors.push("至少需要配置一条规则");
    }

    if (formData.is_send_alert_message && !formData.alert_message_target?.trim()) {
      errors.push("开启告警消息时，告警目标不能为空");
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
      const submitData = {
        ...formData
      };
      const result = await riskControlModelService.create(submitData);
      toast.success("预警管控模型创建成功");
      router.push(`/fraudhunter/risk-control-models/${result.id}`);
    } catch (error: any) {
      console.error("Failed to create risk control model:", error);
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail?.errors) {
        toast.error("创建失败: " + detail.errors.join(", "));
      } else {
        toast.error(detail || "创建失败，请重试");
      }
    } finally {
      setSaving(false);
    }
  };

  // 取消处理
  const handleCancel = () => {
    confirm({
      title: "确认取消",
      description: "确定要取消吗？未保存的更改将丢失",
      onConfirm: () => router.push("/fraudhunter/risk-control-models"),
      variant: "default"
    });
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
  };

  return (
    <>
      <DialogComponent />
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
          </CardContent>
        </Card>

        {/* 规则配置 */}
        <Card>
          <CardHeader>
            <CardTitle>规则配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 导入导出 */}
            <RuleImportExport
              currentRule={formData.rule_config}
              onImport={handleRuleChange}
            />

            {/* 规则构建器 */}
            <RuleBuilder
              indicators={indicators}
              initialRule={formData.rule_config}
              onChange={handleRuleChange}
            />
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
    </>
  );
}
