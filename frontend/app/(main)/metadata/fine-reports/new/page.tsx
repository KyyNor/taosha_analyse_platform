"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { createFineReport, getDesignerUrls, type FineReportCreateData, type DesignerUrl } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function NewFineReportPage() {
  const router = useRouter();
  const { confirm, DialogComponent } = useConfirmDialog();

  const [reportData, setReportData] = useState<FineReportCreateData>({
    report_name: '',
    report_cpt_path: '',
    report_type: 'summary',
    report_design_address: '',
    report_mount_path: '',
    report_mount_type: 'normal',
    department_id: undefined,
    description: '',
    usage_scenario: '',
    is_available: 0, // 默认可用
  });

  const [saving, setSaving] = useState(false);
  const [designerUrls, setDesignerUrls] = useState<DesignerUrl[]>([]);
  const [loadingDesigners, setLoadingDesigners] = useState(true);

  // 加载设计器地址列表
  useEffect(() => {
    const loadDesignerUrls = async () => {
      try {
        const res = await getDesignerUrls();
        setDesignerUrls(res.data || []);
      } catch (error) {
        console.error("加载设计器地址失败:", error);
        toast.error("加载设计器地址失败");
      } finally {
        setLoadingDesigners(false);
      }
    };
    loadDesignerUrls();
  }, []);

  // 报表数据更新处理
  const handleReportDataChange = (field: keyof FineReportCreateData, value: any) => {
    setReportData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!reportData.report_name || reportData.report_name.trim() === '') {
      errors.push('报表名称不能为空');
    }
    if (!reportData.report_cpt_path || reportData.report_cpt_path.trim() === '') {
      errors.push('cpt文件路径不能为空');
    }
    if (!reportData.report_design_address || reportData.report_design_address.trim() === '') {
      errors.push('设计器地址不能为空');
    }
    if (!reportData.report_type) {
      errors.push('报表类型不能为空');
    }

    return errors;
  };

  const handleSave = async () => {
    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      const createResult = await createFineReport(reportData);
      toast.success('FineReport报表创建成功');
      router.push(`/metadata/fine-reports/${createResult.data.id}`);
    } catch (error) {
      console.error('Failed to create FineReport:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async () => {
    const confirmed = await confirm({
      title: "确认取消",
      description: "确定要取消创建报表吗？",
      variant: "default"
    });
    if (confirmed) {
      router.push('/metadata/fine-reports');
    }
  };

  const handleBack = () => {
    router.push('/metadata/fine-reports');
  };

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Plus className="h-6 w-6" />
              新建FineReport报表
            </h1>
            <p className="text-muted-foreground">创建新的FineReport报表元数据</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={saving}
          >
            <X className="h-4 w-4 mr-2" />
            取消
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving}
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? '创建中...' : '创建报表'}
          </Button>
        </div>
      </div>

      {/* 报表基本信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="report-name">报表名称 *</Label>
            <Input
              id="report-name"
              value={reportData.report_name}
              onChange={(e) => handleReportDataChange('report_name', e.target.value)}
              placeholder="请输入报表名称"
            />
          </div>

          <div>
            <Label htmlFor="report-cpt-path">cpt文件路径 *</Label>
            <Input
              id="report-cpt-path"
              value={reportData.report_cpt_path}
              onChange={(e) => handleReportDataChange('report_cpt_path', e.target.value)}
              placeholder="请输入cpt文件路径"
            />
          </div>

          <div>
            <Label htmlFor="report-type">报表类型 *</Label>
            <select
              id="report-type"
              value={reportData.report_type}
              onChange={(e) => handleReportDataChange('report_type', e.target.value as 'summary' | 'detail')}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              <option value="summary">汇总表</option>
              <option value="detail">明细表</option>
            </select>
          </div>

          <div>
            <Label htmlFor="report-design-address">设计器地址 *</Label>
            <select
              id="report-design-address"
              value={reportData.report_design_address}
              onChange={(e) => handleReportDataChange('report_design_address', e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background"
              disabled={loadingDesigners}
            >
              <option value="">
                {loadingDesigners ? '加载中...' : '请选择设计器地址'}
              </option>
              {designerUrls.map((designer) => (
                <option key={designer.url} value={designer.url}>
                  {designer.name} ({designer.url})
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              选择报表所在的设计器地址
            </p>
          </div>

          <div>
            <Label htmlFor="report-mount-path">报表挂载路径</Label>
            <Input
              id="report-mount-path"
              value={reportData.report_mount_path}
              onChange={(e) => handleReportDataChange('report_mount_path', e.target.value)}
              placeholder="请输入报表挂载路径"
            />
            <p className="text-xs text-muted-foreground mt-1">
              报表在系统中的访问路径
            </p>
          </div>

          <div>
            <Label htmlFor="report-mount-type">报表挂载方式 *</Label>
            <select
              id="report-mount-type"
              value={reportData.report_mount_type}
              onChange={(e) => handleReportDataChange('report_mount_type', e.target.value as 'normal' | 'removed')}
              className="w-full px-3 py-2 border rounded-md bg-background"
            >
              <option value="normal">正常</option>
              <option value="removed">已移除</option>
            </select>
            <p className="text-xs text-muted-foreground mt-1">
              报表的挂载状态，已移除表示报表已从系统中删除
            </p>
          </div>

          <div>
            <Label htmlFor="department-id">所属部门ID</Label>
            <Input
              id="department-id"
              type="number"
              value={reportData.department_id || ''}
              onChange={(e) => handleReportDataChange('department_id', e.target.value ? Number(e.target.value) : undefined)}
              placeholder="请输入所属部门ID"
            />
          </div>

          <div>
            <Label htmlFor="report-description">报表说明</Label>
            <Textarea
              id="report-description"
              value={reportData.description}
              onChange={(e) => handleReportDataChange('description', e.target.value)}
              placeholder="请输入报表说明"
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="usage-scenario">适用场景</Label>
            <Textarea
              id="usage-scenario"
              value={reportData.usage_scenario}
              onChange={(e) => handleReportDataChange('usage_scenario', e.target.value)}
              placeholder="请输入报表适用场景"
              rows={3}
            />
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="report-available"
              checked={reportData.is_available === 0}
              onCheckedChange={(checked) => handleReportDataChange('is_available', checked ? 0 : 1)}
            />
            <Label htmlFor="report-available">启用报表</Label>
          </div>
        </CardContent>
      </Card>

      {/* 提示信息 */}
      <Card className="border-l-4 border-l-blue-500">
        <CardContent className="pt-6">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="text-blue-600 text-sm font-medium">i</span>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-800">创建说明</h3>
              <p className="text-sm text-blue-700 mt-1">
                报表创建成功后，将生成唯一的报表ID，可在列表页面进行查看和管理。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      <DialogComponent />
    </div>
  );
}
