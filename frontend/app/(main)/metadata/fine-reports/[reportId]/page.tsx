"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  getFineReportById,
  updateFineReport,
  deleteFineReport,
  getDesignerUrls,
  type FineReport,
  type FineReportUpdateData,
  type DesignerUrl
} from "@/lib/services/metadataService";
import { ArrowLeft, Save, Edit, Trash2, Eye } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

export default function FineReportDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const reportId = parseInt(params.reportId as string);
  const isEditMode = searchParams.get('mode') === 'edit';
  const { confirm, DialogComponent } = useConfirmDialog();

  const [report, setReport] = useState<FineReport | null>(null);
  const [editData, setEditData] = useState<FineReportUpdateData>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(isEditMode);
  const [designerUrls, setDesignerUrls] = useState<DesignerUrl[]>([]);
  const [loadingDesigners, setLoadingDesigners] = useState(true);

  useEffect(() => {
    loadReport();
    loadDesignerUrls();
  }, [reportId]);

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

  const loadReport = async () => {
    setLoading(true);
    try {
      const data = await getFineReportById(reportId);
      setReport(data);
      // 初始化编辑数据
      setEditData({
        report_name: data.report_name,
        report_cpt_path: data.report_cpt_path,
        report_type: data.report_type,
        report_design_address: data.report_design_address,
        report_mount_path: data.report_mount_path,
        report_mount_type: data.report_mount_type,
        department_id: data.department_id,
        description: data.description,
        usage_scenario: data.usage_scenario,
        is_available: data.is_available,
      });
    } catch (error) {
      console.error('Failed to load report:', error);
      toast.error('加载报表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEditDataChange = (field: keyof FineReportUpdateData, value: any) => {
    setEditData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    if (!editData.report_name || editData.report_name.trim() === '') {
      toast.error('报表名称不能为空');
      return;
    }

    setSaving(true);
    try {
      await updateFineReport(reportId, editData);
      toast.success('报表更新成功');
      setEditMode(false);
      loadReport();
    } catch (error) {
      console.error('Failed to update report:', error);
      toast.error('更新失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const confirmed = await confirm({
      title: "确认删除",
      description: `确定要删除报表"${report?.report_name}"吗？`,
      variant: "destructive"
    });
    if (!confirmed) {
      return;
    }

    try {
      await deleteFineReport(reportId);
      toast.success('报表删除成功');
      router.push('/metadata/fine-reports');
    } catch (error) {
      console.error('Failed to delete report:', error);
      toast.error('删除失败，请重试');
    }
  };

  const handleBack = () => {
    router.push('/metadata/fine-reports');
  };

  const handleToggleEditMode = () => {
    if (editMode) {
      // 取消编辑，重置数据
      if (report) {
        setEditData({
          report_name: report.report_name,
          report_cpt_path: report.report_cpt_path,
          report_type: report.report_type,
          report_design_address: report.report_design_address,
          report_mount_path: report.report_mount_path,
          report_mount_type: report.report_mount_type,
          department_id: report.department_id,
          description: report.description,
          usage_scenario: report.usage_scenario,
          is_available: report.is_available,
        });
      }
    }
    setEditMode(!editMode);
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center text-muted-foreground">报表不存在</div>
      </div>
    );
  }

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
              {editMode ? <Edit className="h-6 w-6" /> : <Eye className="h-6 w-6" />}
              {editMode ? '编辑报表' : '报表详情'}
            </h1>
            <p className="text-muted-foreground">{report.report_name}</p>
          </div>
        </div>
        <div className="flex gap-2">
          {editMode ? (
            <>
              <Button
                variant="outline"
                onClick={handleToggleEditMode}
                disabled={saving}
              >
                取消
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
              >
                <Save className="h-4 w-4 mr-2" />
                {saving ? '保存中...' : '保存'}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleToggleEditMode}
              >
                <Edit className="h-4 w-4 mr-2" />
                编辑
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                删除
              </Button>
            </>
          )}
        </div>
      </div>

      {/* 报表信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">报表信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>报表ID</Label>
            <div className="text-sm text-muted-foreground mt-1">{report.id}</div>
          </div>

          <div>
            <Label htmlFor="report-name">报表名称 * <span className="text-xs text-blue-600">(同步字段)</span></Label>
            <div className="text-sm text-muted-foreground mt-1">{report.report_name}</div>
            {editMode && (
              <p className="text-xs text-muted-foreground mt-1">此字段由同步服务管理，不可手动编辑</p>
            )}
          </div>

          <div>
            <Label htmlFor="report-cpt-path">cpt文件路径 * <span className="text-xs text-blue-600">(同步字段)</span></Label>
            <div className="text-sm text-muted-foreground mt-1 font-mono">{report.report_cpt_path}</div>
            {editMode && (
              <p className="text-xs text-muted-foreground mt-1">此字段由同步服务管理，不可手动编辑</p>
            )}
          </div>

          <div>
            <Label htmlFor="report-type">报表类型 *</Label>
            {editMode ? (
              <select
                id="report-type"
                value={editData.report_type}
                onChange={(e) => handleEditDataChange('report_type', e.target.value as 'summary' | 'detail')}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="summary">汇总表</option>
                <option value="detail">明细表</option>
              </select>
            ) : (
              <div className="text-sm text-muted-foreground mt-1">
                {report.report_type === 'summary' ? '汇总表' : '明细表'}
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="report-design-address">设计器地址 * <span className="text-xs text-blue-600">(同步字段)</span></Label>
            <div className="text-sm text-muted-foreground mt-1 font-mono">{report.report_design_address}</div>
            {editMode && (
              <p className="text-xs text-muted-foreground mt-1">此字段由同步服务管理，不可手动编辑</p>
            )}
          </div>

          <div>
            <Label htmlFor="report-mount-path">报表挂载路径 <span className="text-xs text-blue-600">(同步字段)</span></Label>
            <div className="text-sm text-muted-foreground mt-1 font-mono">{report.report_mount_path || '未设置'}</div>
            {editMode && (
              <p className="text-xs text-muted-foreground mt-1">此字段由同步服务管理，不可手动编辑</p>
            )}
          </div>

          <div>
            <Label htmlFor="report-mount-type">报表挂载方式 * <span className="text-xs text-blue-600">(同步字段)</span></Label>
            <div className="text-sm text-muted-foreground mt-1">
              <span className={`px-2 py-1 rounded text-xs ${report.report_mount_type === 'normal' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {report.report_mount_type === 'normal' ? '正常' : '已移除'}
              </span>
            </div>
            {editMode && (
              <p className="text-xs text-muted-foreground mt-1">此字段由同步服务管理，不可手动编辑</p>
            )}
          </div>

          <div>
            <Label htmlFor="department-id">所属部门ID</Label>
            {editMode ? (
              <Input
                id="department-id"
                type="number"
                value={editData.department_id || ''}
                onChange={(e) => handleEditDataChange('department_id', e.target.value ? Number(e.target.value) : undefined)}
              />
            ) : (
              <div className="text-sm text-muted-foreground mt-1">{report.department_id || '未设置'}</div>
            )}
          </div>

          <div>
            <Label htmlFor="report-description">报表说明</Label>
            {editMode ? (
              <Textarea
                id="report-description"
                value={editData.description}
                onChange={(e) => handleEditDataChange('description', e.target.value)}
                rows={3}
              />
            ) : (
              <div className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                {report.description || '无'}
              </div>
            )}
          </div>

          <div>
            <Label htmlFor="usage-scenario">适用场景</Label>
            {editMode ? (
              <Textarea
                id="usage-scenario"
                value={editData.usage_scenario}
                onChange={(e) => handleEditDataChange('usage_scenario', e.target.value)}
                rows={3}
              />
            ) : (
              <div className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                {report.usage_scenario || '无'}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {editMode ? (
              <>
                <Switch
                  id="report-available"
                  checked={editData.is_available === 0}
                  onCheckedChange={(checked) => handleEditDataChange('is_available', checked ? 0 : 1)}
                />
                <Label htmlFor="report-available">启用报表</Label>
              </>
            ) : (
              <>
                <div className={`px-2 py-1 rounded text-xs ${report.is_available === 0 ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                  {report.is_available === 0 ? '可用' : '不可用'}
                </div>
              </>
            )}
          </div>

          <div className="pt-4 border-t">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label>创建时间</Label>
                <div className="text-muted-foreground mt-1">
                  {new Date(report.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <div>
                <Label>更新时间</Label>
                <div className="text-muted-foreground mt-1">
                  {new Date(report.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <DialogComponent />
    </div>
  );
}
