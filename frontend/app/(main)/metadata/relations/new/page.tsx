"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createRelation } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus, Link } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

interface NewRelationConfig {
  relation_family: string;
  relation_subfamily: string;
  relation_desc: string;
}

export default function NewRelationConfigPage() {
  const router = useRouter();
  const { confirm, DialogComponent } = useConfirmDialog();

  const [relationData, setRelationData] = useState<NewRelationConfig>({
    relation_family: '',
    relation_subfamily: '',
    relation_desc: '',
  });

  const [saving, setSaving] = useState(false);

  // 关系配置数据更新处理
  const handleRelationDataChange = (field: keyof NewRelationConfig, value: any) => {
    setRelationData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证基本信息
    if (!relationData.relation_family || relationData.relation_family.trim() === '') {
      errors.push('关系族不能为空');
    }

    if (!relationData.relation_subfamily || relationData.relation_subfamily.trim() === '') {
      errors.push('关系子族不能为空');
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
      const createResult = await createRelation({
        relation_family: relationData.relation_family,
        relation_subfamily: relationData.relation_subfamily,
        relation_desc: relationData.relation_desc,
      });

      toast.success('关系配置创建成功');
      router.push(`/metadata/relations/${createResult.data.id}`);
    } catch (error) {
      console.error('Failed to create relation config:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async () => {
    const confirmed = await confirm({
      title: "确认取消",
      description: "确定要取消创建关系配置吗？",
      variant: "default"
    });
    if (confirmed) {
      router.push('/metadata/relations');
    }
  };

  const handleBack = () => {
    router.push('/metadata/relations');
  };

  // 生成关系ID预览
  const relationIdPreview = `${relationData.relation_family || 'family'}|${relationData.relation_subfamily || 'subfamily'}`;

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
              新建关系配置
            </h1>
            <p className="text-muted-foreground">创建新的数据表关联关系配置</p>
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
            {saving ? '创建中...' : '创建配置'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主要内容 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="relation-family">关系族 *</Label>
                  <Input
                    id="relation-family"
                    value={relationData.relation_family}
                    onChange={(e) => handleRelationDataChange('relation_family', e.target.value)}
                    placeholder="例如：用户、订单、产品"
                  />
                  <p className="mt-1 text-sm text-gray-500">定义大的关系类别，如用户关系、订单关系等</p>
                </div>
                <div>
                  <Label htmlFor="relation-subfamily">关系子族 *</Label>
                  <Input
                    id="relation-subfamily"
                    value={relationData.relation_subfamily}
                    onChange={(e) => handleRelationDataChange('relation_subfamily', e.target.value)}
                    placeholder="例如：一对多、主外键、依赖"
                  />
                  <p className="mt-1 text-sm text-gray-500">定义具体的关系类型，如一对多、依赖关系等</p>
                </div>
              </div>
              <div>
                <Label htmlFor="relation-desc">关系描述</Label>
                <Textarea
                  id="relation-desc"
                  value={relationData.relation_desc}
                  onChange={(e) => handleRelationDataChange('relation_desc', e.target.value)}
                  placeholder="请输入关系的详细描述和用途说明"
                  rows={4}
                />
                <p className="mt-1 text-sm text-gray-500">详细描述该关联关系的含义、使用场景和注意事项</p>
              </div>
            </CardContent>
          </Card>

          {/* 关系ID预览 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">关系ID预览</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-blue-700">生成的关系ID:</span>
                  <code className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-mono">
                    {relationIdPreview}
                  </code>
                </div>
                <p className="text-sm text-blue-600">
                  这个标识符将在系统中唯一标识该关联关系，用于字段配置时选择关联类型。
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
          {/* 配置说明 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">配置说明</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p><strong>关系族：</strong>定义大的关系类别</p>
                    <p><strong>关系子族：</strong>定义具体的关系类型</p>
                    <p><strong>组合格式：</strong>关系族|关系子族</p>
                    <p><strong>唯一标识：</strong>用于字段配置中引用</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 常见示例 */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-green-600 text-sm font-medium">✓</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">常见示例</h3>
                  <div className="mt-2 text-sm text-green-700 space-y-1">
                    <p><code>用户|一对多</code> - 用户与订单的一对多关系</p>
                    <p><code>订单|主外键</code> - 订单表的主外键关系</p>
                    <p><code>产品|依赖</code> - 产品之间的依赖关系</p>
                    <p><code>分类|层级</code> - 分类的层级关系</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 使用提示 */}
          <Card className="border-l-4 border-l-yellow-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                    <span className="text-yellow-600 text-sm font-medium">!</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-yellow-800">使用提示</h3>
                  <p className="mt-1 text-sm text-yellow-700">
                    创建关系配置后，可以在元数据管理的表字段编辑页面中为字段选择相应的关联关系，帮助系统更好地理解数据结构。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      <DialogComponent />
    </div>
  );
}