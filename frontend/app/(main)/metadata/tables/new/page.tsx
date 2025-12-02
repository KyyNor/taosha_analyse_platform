"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { createTable } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus } from "lucide-react";
import { toast } from "sonner";

interface NewTable {
  name: string;
  comment: string;
  remark: string;
  is_available: number; // 0=可用，1=不可用
}

export default function NewTablePage() {
  const router = useRouter();

  const [tableData, setTableData] = useState<NewTable>({
    name: '',
    comment: '',
    remark: '',
    is_available: 0, // 默认可用
  });

  const [saving, setSaving] = useState(false);

  // 表数据更新处理
  const handleTableDataChange = (field: keyof NewTable, value: any) => {
    setTableData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证表基本信息
    if (!tableData.name || tableData.name.trim() === '') {
      errors.push('表名不能为空');
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
      // 创建表（暂时只创建基本信息，字段需要在表详情页面添加）
      const createResult = await createTable({
        name: tableData.name,
        comment: tableData.comment,
        remark: tableData.remark,
        is_available: tableData.is_available,
      });

      toast.success('表创建成功，您可以在详情页面添加字段信息');
      router.push(`/metadata/tables/${createResult.data.id}`);
    } catch (error) {
      console.error('Failed to create table:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (confirm('确定要取消创建表吗？')) {
      router.push('/metadata/tables');
    }
  };

  const handleBack = () => {
    router.push('/metadata/tables');
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
              新建数据表
            </h1>
            <p className="text-muted-foreground">创建新的数据表和字段信息</p>
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
            {saving ? '创建中...' : '创建表'}
          </Button>
        </div>
      </div>

      {/* 表基本信息 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="table-name">表名 *</Label>
            <Input
              id="table-name"
              value={tableData.name}
              onChange={(e) => handleTableDataChange('name', e.target.value)}
              placeholder="请输入表名"
            />
          </div>
          <div>
            <Label htmlFor="table-comment">表描述</Label>
            <Textarea
              id="table-comment"
              value={tableData.comment}
              onChange={(e) => handleTableDataChange('comment', e.target.value)}
              placeholder="请输入表描述"
              rows={3}
            />
          </div>
          <div>
            <Label htmlFor="table-remark">备注</Label>
            <Textarea
              id="table-remark"
              value={tableData.remark}
              onChange={(e) => handleTableDataChange('remark', e.target.value)}
              placeholder="请输入备注"
              rows={2}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="table-available"
              checked={tableData.is_available === 0}
              onCheckedChange={(checked) => handleTableDataChange('is_available', checked ? 0 : 1)}
            />
            <Label htmlFor="table-available">启用表</Label>
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
              <h3 className="text-sm font-medium text-blue-800">创建后操作</h3>
              <p className="text-sm text-blue-700 mt-1">
                表创建成功后，您可以在详情页面添加和管理字段信息。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}