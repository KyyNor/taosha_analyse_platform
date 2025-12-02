"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { getRelationById, updateRelation } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Edit3, Eye } from "lucide-react";
import { toast } from "sonner";

interface RelationConfig {
  id: number;
  relation_id: string;
  relation_family: string;
  relation_subfamily: string;
  relation_desc: string;
  created_at: string;
  updated_at: string;
}

export default function RelationConfigDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const configId = params.configId as string;
  const mode = searchParams.get("mode") || "view";

  const [relationData, setRelationData] = useState<RelationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 加载关系配置数据
  const loadRelationConfig = async () => {
    setLoading(true);
    try {
      const res = await getRelationById(Number(configId));
      if (res.success) {
        setRelationData(res.data);
      } else {
        toast.error("加载关系配置数据失败");
      }
    } catch (error) {
      console.error("Failed to load relation config:", error);
      toast.error("加载关系配置数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (configId) {
      loadRelationConfig();
    }
  }, [configId]);

  // 数据更新处理
  const handleRelationDataChange = (field: keyof RelationConfig, value: any) => {
    if (!relationData) return;

    setRelationData(prev => ({
      ...prev!,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!relationData) return errors;

    // 验证基本信息
    if (!relationData.relation_family || relationData.relation_family.trim() === '') {
      errors.push('关系族不能为空');
    }

    if (!relationData.relation_subfamily || relationData.relation_subfamily.trim() === '') {
      errors.push('关系子族不能为空');
    }

    return errors;
  };

  // 保存处理
  const handleSave = async () => {
    if (!relationData) return;

    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      await updateRelation(Number(configId), {
        relation_family: relationData.relation_family,
        relation_subfamily: relationData.relation_subfamily,
        relation_desc: relationData.relation_desc,
      });

      toast.success('关系配置更新成功');
      if (mode === "edit") {
        router.push(`/metadata/relations/${configId}`);
      } else {
        await loadRelationConfig(); // 重新加载数据
      }
    } catch (error) {
      console.error('Failed to update relation config:', error);
      toast.error('更新失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 切换编辑模式
  const handleEdit = () => {
    router.push(`/metadata/relations/${configId}?mode=edit`);
  };

  // 取消编辑
  const handleCancel = () => {
    if (confirm('确定要取消编辑吗？未保存的更改将丢失。')) {
      if (mode === "edit") {
        router.push(`/metadata/relations/${configId}`);
      } else {
        router.push('/metadata/relations');
      }
    }
  };

  // 返回列表
  const handleBack = () => {
    router.push('/metadata/relations');
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-6"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="h-40 bg-gray-200 rounded"></div>
              <div className="h-40 bg-gray-200 rounded"></div>
            </div>
            <div className="h-40 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!relationData) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">关系配置不存在</h2>
          <p className="text-gray-600 mb-6">请检查配置ID是否正确</p>
          <Button onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回列表
          </Button>
        </div>
      </div>
    );
  }

  const isEditing = mode === "edit";

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
              {isEditing ? <Edit3 className="h-6 w-6" /> : <Eye className="h-6 w-6" />}
              {isEditing ? "编辑关系配置" : "关系配置详情"}
            </h1>
            <p className="text-muted-foreground">
              管理数据表之间的关联关系配置信息
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {!isEditing ? (
            <Button onClick={handleEdit}>
              <Edit3 className="h-4 w-4 mr-2" />
              编辑
            </Button>
          ) : (
            <>
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
                {saving ? '保存中...' : '保存'}
              </Button>
            </>
          )}
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
                  {isEditing ? (
                    <Input
                      id="relation-family"
                      value={relationData.relation_family}
                      onChange={(e) => handleRelationDataChange('relation_family', e.target.value)}
                      placeholder="请输入关系族名称"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {relationData.relation_family}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="relation-subfamily">关系子族 *</Label>
                  {isEditing ? (
                    <Input
                      id="relation-subfamily"
                      value={relationData.relation_subfamily}
                      onChange={(e) => handleRelationDataChange('relation_subfamily', e.target.value)}
                      placeholder="请输入关系子族名称"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {relationData.relation_subfamily}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <Label htmlFor="relation-desc">关系描述</Label>
                {isEditing ? (
                  <Textarea
                    id="relation-desc"
                    value={relationData.relation_desc}
                    onChange={(e) => handleRelationDataChange('relation_desc', e.target.value)}
                    placeholder="请输入关系的详细描述"
                    rows={4}
                  />
                ) : (
                  <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] whitespace-pre-wrap">
                    {relationData.relation_desc || '暂无描述'}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 关联关系展示 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">关联关系标识</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-blue-700">关系ID:</span>
                  <code className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-mono">
                    {relationData.relation_id}
                  </code>
                </div>
                <p className="text-sm text-blue-600">
                  这个标识符用于在系统中唯一标识该关联关系，通常由关系族和关系子族组合而成。
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
          {/* 元数据信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">元数据信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label className="text-sm font-medium text-gray-700">配置ID</Label>
                <div className="mt-1 text-sm text-gray-900">{relationData.id}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">关系ID</Label>
                <div className="mt-1 text-sm text-gray-900 font-mono">
                  {relationData.relation_id}
                </div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">创建时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(relationData.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">更新时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(relationData.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 使用说明 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">关系配置说明</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p><strong>关系族：</strong>定义大的关系类别</p>
                    <p><strong>关系子族：</strong>定义具体的关系类型</p>
                    <p><strong>组合标识：</strong>用于在字段配置中引用</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 使用提示 */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-green-600 text-sm font-medium">✓</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">使用提示</h3>
                  <p className="mt-1 text-sm text-green-700">
                    创建关系配置后，可以在表字段编辑时选择相应的关联关系，帮助系统理解字段间的业务联系。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}