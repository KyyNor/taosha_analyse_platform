"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { getPromptTemplateById, updatePromptTemplate } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Edit3, Eye, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface PromptTemplate {
  id: number;
  name: string;
  fields: any[];
  template: string;
  created_at: string;
  updated_at: string;
}

interface TemplateField {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export default function PromptTemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateId = params.templateId as string;
  const mode = searchParams.get("mode") || "view";

  const [templateData, setTemplateData] = useState<PromptTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 加载提示词模板数据
  const loadTemplate = async () => {
    setLoading(true);
    try {
      const res = await getPromptTemplateById(Number(templateId));
      if (res.success) {
        setTemplateData(res.data);
      } else {
        toast.error("加载提示词模板数据失败");
      }
    } catch (error) {
      console.error("Failed to load prompt template:", error);
      toast.error("加载提示词模板数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (templateId) {
      loadTemplate();
    }
  }, [templateId]);

  // 数据更新处理
  const handleTemplateDataChange = (field: keyof PromptTemplate, value: any) => {
    if (!templateData) return;

    setTemplateData(prev => ({
      ...prev!,
      [field]: value
    }));
  };

  // 字段数据更新处理
  const handleFieldsChange = (index: number, field: keyof TemplateField, value: any) => {
    if (!templateData) return;

    const updatedFields = [...templateData.fields];
    updatedFields[index] = {
      ...updatedFields[index],
      [field]: value
    };

    setTemplateData(prev => ({
      ...prev!,
      fields: updatedFields
    }));
  };

  // 添加新字段
  const addField = () => {
    if (!templateData) return;

    const newField: TemplateField = {
      name: '',
      type: 'string',
      required: false,
      description: ''
    };

    setTemplateData(prev => ({
      ...prev!,
      fields: [...prev!.fields, newField]
    }));
  };

  // 删除字段
  const removeField = (index: number) => {
    if (!templateData) return;

    const updatedFields = templateData.fields.filter((_, i) => i !== index);
    setTemplateData(prev => ({
      ...prev!,
      fields: updatedFields
    }));
  };

  // 验证字段配置中的占位符
  const validatePlaceholders = () => {
    if (!templateData) return [];

    const errors: string[] = [];
    const templateText = templateData.template;
    const fieldNames = templateData.fields.map(field => field.name).filter(name => name);

    // 查找模板中的占位符 {{field_name}}
    const placeholderRegex = /\{\{([^}]+)\}\}/g;
    const placeholders = [];
    let match;

    while ((match = placeholderRegex.exec(templateText)) !== null) {
      placeholders.push(match[1].trim());
    }

    // 检查模板中使用了未定义的字段
    const undefinedFields = placeholders.filter(placeholder =>
      !fieldNames.includes(placeholder)
    );

    // 检查定义了但模板中未使用的字段
    const unusedFields = fieldNames.filter(fieldName =>
      !placeholders.includes(fieldName)
    );

    if (undefinedFields.length > 0) {
      errors.push(`模板中使用了未定义的字段: ${undefinedFields.join(', ')}`);
    }

    if (unusedFields.length > 0) {
      errors.push(`定义了但模板中未使用的字段: ${unusedFields.join(', ')}`);
    }

    return errors;
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!templateData) return errors;

    // 验证基本信息
    if (!templateData.name || templateData.name.trim() === '') {
      errors.push('模板名称不能为空');
    }

    if (!templateData.template || templateData.template.trim() === '') {
      errors.push('模板内容不能为空');
    }

    // 验证字段配置
    for (let i = 0; i < templateData.fields.length; i++) {
      const field = templateData.fields[i];
      if (!field.name || field.name.trim() === '') {
        errors.push(`字段 ${i + 1} 的名称不能为空`);
      }
    }

    // 验证占位符
    const placeholderErrors = validatePlaceholders();
    errors.push(...placeholderErrors);

    return errors;
  };

  // 保存处理
  const handleSave = async () => {
    if (!templateData) return;

    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      await updatePromptTemplate(Number(templateId), {
        name: templateData.name,
        fields: templateData.fields,
        template: templateData.template,
      });

      toast.success('提示词模板更新成功');
      if (mode === "edit") {
        router.push(`/metadata/prompt-templates/${templateId}`);
      } else {
        await loadTemplate(); // 重新加载数据
      }
    } catch (error) {
      console.error('Failed to update prompt template:', error);
      toast.error('更新失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 切换编辑模式
  const handleEdit = () => {
    router.push(`/metadata/prompt-templates/${templateId}?mode=edit`);
  };

  // 取消编辑
  const handleCancel = () => {
    if (confirm('确定要取消编辑吗？未保存的更改将丢失。')) {
      if (mode === "edit") {
        router.push(`/metadata/prompt-templates/${templateId}`);
      } else {
        router.push('/metadata/prompt-templates');
      }
    }
  };

  // 返回列表
  const handleBack = () => {
    router.push('/metadata/prompt-templates');
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
              <div className="h-60 bg-gray-200 rounded"></div>
            </div>
            <div className="h-40 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!templateData) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">提示词模板不存在</h2>
          <p className="text-gray-600 mb-6">请检查模板ID是否正确</p>
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
    <div className="container mx-auto py-6">
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
              {isEditing ? "编辑提示词模板" : "提示词模板详情"}
            </h1>
            <p className="text-muted-foreground">
              管理AI查询的提示词模板和字段配置
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
              <div>
                <Label htmlFor="template-name">模板名称 *</Label>
                {isEditing ? (
                  <Input
                    id="template-name"
                    value={templateData.name}
                    onChange={(e) => handleTemplateDataChange('name', e.target.value)}
                    placeholder="请输入模板名称"
                  />
                ) : (
                  <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                    {templateData.name}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 字段配置 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                字段配置
                {isEditing && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addField}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    添加字段
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {templateData.fields.length === 0 ? (
                <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded">
                  暂无字段配置
                  {isEditing && (
                    <p className="text-sm mt-2">点击上方"添加字段"按钮开始配置</p>
                  )}
                </div>
              ) : (
                templateData.fields.map((field: any, index: number) => (
                  <div key={index} className="border rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">字段 {index + 1}</h4>
                      {isEditing && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeField(index)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          删除
                        </Button>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor={`field-name-${index}`}>字段名称 *</Label>
                        {isEditing ? (
                          <Input
                            id={`field-name-${index}`}
                            value={field.name}
                            onChange={(e) => handleFieldsChange(index, 'name', e.target.value)}
                            placeholder="例如：user_query"
                          />
                        ) : (
                          <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                            {field.name}
                          </div>
                        )}
                      </div>
                      <div>
                        <Label htmlFor={`field-type-${index}`}>字段类型</Label>
                        {isEditing ? (
                          <Input
                            id={`field-type-${index}`}
                            value={field.type}
                            onChange={(e) => handleFieldsChange(index, 'type', e.target.value)}
                            placeholder="例如：string, number"
                          />
                        ) : (
                          <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                            {field.type}
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <Label htmlFor={`field-desc-${index}`}>字段描述</Label>
                      {isEditing ? (
                        <Textarea
                          id={`field-desc-${index}`}
                          value={field.description}
                          onChange={(e) => handleFieldsChange(index, 'description', e.target.value)}
                          placeholder="请输入字段的用途说明"
                          rows={2}
                        />
                      ) : (
                        <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] whitespace-pre-wrap">
                          {field.description || '暂无描述'}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* 模板内容 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">模板内容 *</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 mb-4">
                <Label>使用说明</Label>
                <p className="text-sm text-gray-600">
                  在模板中使用双花括号引用字段，如 <code className="px-1 py-0.5 bg-gray-100 rounded">{"{{user_query}}"}</code>
                </p>
              </div>
              {isEditing ? (
                <Textarea
                  value={templateData.template}
                  onChange={(e) => handleTemplateDataChange('template', e.target.value)}
                  placeholder="请输入提示词模板内容，使用 {{field_name}} 格式引用字段"
                  rows={12}
                  className="font-mono text-sm"
                />
              ) : (
                <div className="bg-gray-50 rounded border p-4 min-h-[200px] whitespace-pre-wrap font-mono text-sm">
                  {templateData.template}
                </div>
              )}
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
                <Label className="text-sm font-medium text-gray-700">模板ID</Label>
                <div className="mt-1 text-sm text-gray-900">{templateData.id}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">字段数量</Label>
                <div className="mt-1 text-sm text-gray-900">{templateData.fields.length} 个</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">创建时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(templateData.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">更新时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(templateData.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 字段预览 */}
          {templateData.fields.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">字段预览</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {templateData.fields.map((field: any, index: number) => (
                  <div key={index} className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {field.name || `field${index + 1}`}
                    </Badge>
                    <span className="text-xs text-gray-500">{field.type}</span>
                    {field.required && (
                      <Badge variant="destructive" className="text-xs">必需</Badge>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* 使用指南 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">使用指南</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p>• 字段名称在模板中使用双花括号引用</p>
                    <p>• 确保所有使用的字段都已定义</p>
                    <p>• 建议为字段提供清晰的描述</p>
                    <p>• 模板内容应包含完整的使用说明</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}