"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, FileCode, AlertCircle } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
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
import { riskControlModelService } from "@/lib/services/fraudhunterService";
import { indicatorService } from "@/lib/services/fraudhunterService";
import { modelService } from "@/lib/services/fraudhunter/modelService";
import type {
  RiskControlModel,
  RiskControlModelUpdate,
  RiskControlModelPublishRequest
} from "@/types/fraudhunter/risk-control-model";
import type { RuleConfig, Indicator } from "@/types/fraudhunter/rule";
import { RuleBuilder } from "@/components/fraudhunter/model/RuleBuilder";
import { RuleImportExport } from "@/components/fraudhunter/model/RuleImportExport";
import {
  getModelStatusLabel,
  getModelStatusVariant
} from "@/types/fraudhunter/risk-control-model";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function RiskControlModelDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const modelId = Number(params?.id);
  const mode = searchParams?.get("mode");
  const { confirm, DialogComponent } = useConfirmDialog();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatingSQL, setGeneratingSQL] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === "edit");
  const [data, setData] = useState<RiskControlModel | null>(null);
  const [originalData, setOriginalData] = useState<RiskControlModel | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [sqlPreview, setSqlPreview] = useState<string>("");

  // 发布对话框状态
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [publishData, setPublishData] = useState<RiskControlModelPublishRequest>({
    version: 1,
    change_description: ""
  });

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await riskControlModelService.get(modelId);
      setData(result);
      setOriginalData(JSON.parse(JSON.stringify(result)));

      // 设置SQL预览
      if (result.offline_model_sql) {
        setSqlPreview(result.offline_model_sql);
      }

      // 设置发布数据默认版本
      setPublishData(prev => ({ ...prev, version: result.latest_version }));
    } catch (error) {
      console.error("Failed to load risk control model:", error);
      toast.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 加载指标
    const loadIndicators = async () => {
      try {
        const response = await indicatorService.list({
          status: "online",
          query_type: "all"
        });
        // 转换为规则引擎需要的格式，包含indicator_type
        const transformedIndicators: Indicator[] = (response.items || []).map(item => ({
          id: item.id,
          indicator_code: item.indicator_code,
          indicator_name: item.indicator_name,
          data_type: item.data_type,
          indicator_type: item.indicator_type as 'offline' | 'realtime' | undefined,
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
    loadData();
  }, [modelId]);

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
  const updateField = <K extends keyof RiskControlModel>(
    field: K,
    value: RiskControlModel[K]
  ) => {
    if (!data) return;
    setData({ ...data, [field]: value });
  };

  // 规则变化处理
  const handleRuleChange = (newRule: RuleConfig) => {
    updateField("rule_config", newRule);
  };

  // 重新生成SQL
  const handleRegenerateSQL = async () => {
    if (!data || !data.rule_config) return;

    setGeneratingSQL(true);
    try {
      const result = await modelService.previewSQL(data.rule_config);
      setSqlPreview(result.sql_expression);
      toast.success("SQL已重新生成");
    } catch (error: any) {
      console.error("Failed to generate SQL:", error);
      const detail = error.response?.data?.detail;
      if (detail?.errors) {
        toast.error("SQL生成失败: " + detail.errors.join(", "));
      } else {
        toast.error(detail?.message || "SQL生成失败");
      }
    } finally {
      setGeneratingSQL(false);
    }
  };

  // 保存
  const handleSave = async () => {
    if (!data || !hasChanges) return;

    setSaving(true);
    try {
      const updateData: RiskControlModelUpdate = {
        model_name: data.model_name,
        description: data.description,
        rule_config: data.rule_config,
        is_send_alert_message: data.is_send_alert_message,
        alert_message_target: data.alert_message_target,
        is_acct_control: data.is_acct_control,
        is_send_financial_manager_alert: data.is_send_financial_manager_alert
      };

      await riskControlModelService.update(modelId, updateData);
      toast.success("保存成功");
      await loadData();
      router.push(`/fraudhunter/risk-control-models/${modelId}`);
    } catch (error: any) {
      console.error("Failed to update risk control model:", error);
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail?.errors) {
        toast.error("保存失败: " + detail.errors.join(", "));
      } else {
        toast.error(detail || "保存失败");
      }
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
          router.push(`/fraudhunter/risk-control-models/${modelId}`);
        }
      });
    } else {
      router.push(`/fraudhunter/risk-control-models/${modelId}`);
    }
  };

  // 进入编辑模式
  const handleEdit = () => {
    router.push(`/fraudhunter/risk-control-models/${modelId}?mode=edit`);
  };

  // 发布
  const handlePublish = async () => {
    if (!publishData.version || publishData.version < 1) {
      toast.error("请输入有效的版本号");
      return;
    }

    try {
      await riskControlModelService.publish(modelId, publishData);
      toast.success("发布成功");
      setPublishDialogOpen(false);
      await loadData();
    } catch (error: any) {
      console.error("Failed to publish risk control model:", error);
      toast.error(error.response?.data?.detail || "发布失败");
    }
  };

  // 归档
  const handleArchive = () => {
    confirm({
      title: "确认归档",
      description: "确定要归档此模型吗？",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await riskControlModelService.archive(modelId);
          toast.success("归档成功");
          await loadData();
        } catch (error: any) {
          console.error("Failed to archive risk control model:", error);
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
        <div className="text-center">预警管控模型不存在</div>
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
            onClick={() => router.push("/fraudhunter/risk-control-models")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{data.model_name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={getModelStatusVariant(data.status)}>
                {getModelStatusLabel(data.status)}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {data.model_code}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {!isEditMode ? (
            <>
              <Button variant="outline" onClick={handleEdit}>
                编辑
              </Button>
              <Button
                variant="outline"
                onClick={() => setPublishDialogOpen(true)}
                disabled={data.status === "archived"}
              >
                发布
              </Button>
              <Button
                variant="outline"
                onClick={handleArchive}
                disabled={data.status === "archived"}
              >
                归档
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={handleCancel}>
                取消
              </Button>
              <Button onClick={handleSave} disabled={saving || !hasChanges}>
                {saving ? "保存中..." : "保存"}
              </Button>
            </>
          )}
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
              <Label>模型编码</Label>
              <Input value={data.model_code} disabled />
            </div>

            <div>
              <Label htmlFor="model-name">模型名称</Label>
              {isEditMode ? (
                <Input
                  id="model-name"
                  value={data.model_name}
                  onChange={(e) => updateField("model_name", e.target.value)}
                  maxLength={128}
                />
              ) : (
                <Input value={data.model_name} disabled />
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
                <Textarea value={data.description || ""} disabled rows={3} />
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>当前版本</Label>
                <Input value={data.current_version} disabled />
              </div>
              <div>
                <Label>最新版本</Label>
                <Input value={data.latest_version} disabled />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 规则配置 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>规则配置</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 导入导出 - 仅在编辑模式下显示 */}
            {isEditMode && (
              <RuleImportExport
                currentRule={data.rule_config}
                onImport={handleRuleChange}
              />
            )}
            <RuleBuilder
              indicators={indicators}
              initialRule={data.rule_config}
              onChange={handleRuleChange}
              readOnly={!isEditMode}
            />
          </CardContent>
        </Card>

        {/* SQL预览 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>离线模型SQL</CardTitle>
              {isEditMode && (
                <Button
                  variant="outline"
                  onClick={handleRegenerateSQL}
                  disabled={generatingSQL}
                >
                  <FileCode className="h-4 w-4 mr-2" />
                  {generatingSQL ? "生成中..." : "重新生成"}
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {sqlPreview ? (
              <pre className="bg-muted p-4 rounded-md overflow-x-auto text-sm">
                {sqlPreview}
              </pre>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>暂无SQL</p>
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
                checked={data.is_send_alert_message}
                onCheckedChange={(checked) =>
                  updateField("is_send_alert_message", checked as boolean)
                }
                disabled={!isEditMode}
              />
              <Label htmlFor="send-alert" className={isEditMode ? "cursor-pointer" : ""}>
                发送告警消息
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="acct-control"
                checked={data.is_acct_control}
                onCheckedChange={(checked) =>
                  updateField("is_acct_control", checked as boolean)
                }
                disabled={!isEditMode}
              />
              <Label htmlFor="acct-control" className={isEditMode ? "cursor-pointer" : ""}>
                账户控制
              </Label>
            </div>

            {/* ======= 【新增】理财经理告警选项 ======= */}
            {data.is_send_alert_message && (
              <>
                <Separator className="my-2" />
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="send-financial-manager"
                    checked={data.is_send_financial_manager_alert ?? false}
                    onCheckedChange={(checked) =>
                      updateField("is_send_financial_manager_alert", checked as boolean)
                    }
                    disabled={!isEditMode}
                  />
                  <Label
                    htmlFor="send-financial-manager"
                    className={isEditMode ? "cursor-pointer" : ""}
                    title="需同步开启「发送告警消息」方可生效"
                  >
                    同时发送给理财经理
                  </Label>
                </div>
                <p className="text-xs text-muted-foreground ml-7">
                  通过客户号查表发送给对应的理财经理
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* 审计信息 */}
        <Card>
          <CardHeader>
            <CardTitle>审计信息</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div>
              <Label>创建人</Label>
              <Input value={data.created_by || "-"} disabled />
            </div>
            <div>
              <Label>创建时间</Label>
              <Input
                value={new Date(data.created_at).toLocaleString()}
                disabled
              />
            </div>
            <div>
              <Label>更新人</Label>
              <Input value={data.updated_by || "-"} disabled />
            </div>
            <div>
              <Label>更新时间</Label>
              <Input
                value={new Date(data.updated_at).toLocaleString()}
                disabled
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 发布对话框 */}
      <Dialog open={publishDialogOpen} onOpenChange={setPublishDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>发布预警管控模型</DialogTitle>
            <DialogDescription>
              发布模型到指定版本，使其上线生效
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="publish-version">版本号</Label>
              <Input
                id="publish-version"
                type="number"
                min={1}
                max={data.latest_version}
                value={publishData.version}
                onChange={(e) =>
                  setPublishData({ ...publishData, version: parseInt(e.target.value) })
                }
              />
              <p className="text-sm text-muted-foreground mt-1">
                请输入1到{data.latest_version}之间的版本号
              </p>
            </div>
            <div>
              <Label htmlFor="publish-description">变更说明</Label>
              <Textarea
                id="publish-description"
                value={publishData.change_description || ""}
                onChange={(e) =>
                  setPublishData({ ...publishData, change_description: e.target.value })
                }
                placeholder="描述本次发布的变更内容（可选）"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPublishDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handlePublish}>
              确认发布
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <DialogComponent />
    </div>
  );
}
