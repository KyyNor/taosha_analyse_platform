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
  fields: string[];
  template: string;
  created_at: string;
  updated_at: string;
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
  const handleFieldsChange = (index: number, value: string) => {
    if (!templateData) return;

    const updatedFields = [...templateData.fields];
    updatedFields[index] = value;

    setTemplateData(prev => ({
      ...prev!,
      fields: updatedFields
    }));
  };

  // 添加新字段
  const addField = () => {
    if (!templateData) return;

    setTemplateData(prev => ({
      ...prev!,
      fields: [...prev!.fields, '']
    }));
  };

  // 删除字段
  const removeField = (index: number) => {
    if (!templateData) return;

    // 至少保留一个字段
    if (templateData.fields.length > 1) {
      const updatedFields = templateData.fields.filter((_, i) => i !== index);
      setTemplateData(prev => ({
        ...prev!,
        fields: updatedFields
      }));
    }
  };

  // 验证字段配置中的占位符
  const validatePlaceholders = () => {
    if (!templateData) return [];

    const errors: string[] = [];
    const templateText = templateData.template;
    const fieldNames = templateData.fields.filter(name => name.trim());

    // 查找模板中的占位符 {field_name}，严格匹配{}格式，避免匹配{{}}或JSON
    const placeholderRegex = /(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})/g;
    const placeholders = new Set<string>();
    let match;

    while ((match = placeholderRegex.exec(templateText)) !== null) {
      placeholders.add(match[1]);
    }

    // 如果字段列表为空且没有占位符，这是无参数模板，完全有效
    if (fieldNames.length === 0 && placeholders.size === 0) {
      return errors;
    }

    // 检查模板中使用了未定义的字段
    const definedFields = new Set(fieldNames);
    const missingFields = Array.from(placeholders).filter(p => !definedFields.has(p));
    if (missingFields.length > 0) {
      errors.push(`模板中使用了未定义的字段: ${missingFields.join(', ')}`);
    }

    // 检查定义了但模板中未使用的字段
    const unusedFields = fieldNames.filter(fieldName => !placeholders.has(fieldName));
    if (unusedFields.length > 0) {
      errors.push(`字段列表中有未使用的字段: ${unusedFields.join(', ')}`);
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
      // 过滤掉空白字段
      const fieldsArray = templateData.fields.filter(f => f.trim());

      await updatePromptTemplate(Number(templateId), {
        name: templateData.name,
        fields: fieldsArray,
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
              <div className="space-y-2">
                {templateData.fields.map((field: string, index: number) => (
                  <div key={index} className="flex gap-2 items-center">
                    {isEditing ? (
                      <>
                        <Input
                          value={field}
                          onChange={(e) => handleFieldsChange(index, e.target.value)}
                          placeholder="字段名（如：user_input）"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeField(index)}
                          disabled={templateData.fields.length <= 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <div className="w-full p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                        {field || '(空白字段)'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {isEditing && (
                <p className="text-sm text-gray-500 mt-2">
                  字段名将在模板中作为占位符使用，格式：<code className="px-1 py-0.5 bg-gray-100 rounded">{"{字段名}"}</code>。不添加字段表示模板没有参数（固定内容）。
                </p>
              )}
            </CardContent>
          </Card>

          {/* 模板内容 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">提示词模板 *</CardTitle>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <>
                  <Textarea
                    value={templateData.template}
                    onChange={(e) => handleTemplateDataChange('template', e.target.value)}
                    placeholder="请输入提示词模板，使用 {字段名} 作为占位符"
                    rows={12}
                    className="font-mono text-sm"
                  />
                  <div className="mt-2 p-4 bg-gray-50 rounded-lg border">
                    <p className="text-sm">
                      <span className="text-amber-600 font-medium">★ 占位符格式：</span>
                      使用 <span className="font-mono bg-amber-100 px-1 py-0.5 rounded">{"{字段名}"}</span> 标记占位符，
                      使用 <span className="font-mono bg-amber-100 px-1 py-0.5 rounded">{"@[模板名称]"}</span> 标记模板替换
                    </p>
                  </div>
                </>
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
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">字段列表</CardTitle>
            </CardHeader>
            <CardContent>
              {templateData.fields.filter(f => f.trim()).length === 0 ? (
                <p className="text-sm text-gray-500 italic">无参数模板</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {templateData.fields.filter(f => f.trim()).map((field: string, index: number) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {field}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

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
                    <p>• 占位符格式：使用单花括号 {"{字段名}"} 标记变量</p>
                    <p>• 模板引用：使用 {"@[模板名称]"} 引用其他模板</p>
                    <p>• 无参数模板：字段为空时表示模板包含固定内容</p>
                    <p>• 严格匹配：系统会验证占位符与字段的一致性</p>
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