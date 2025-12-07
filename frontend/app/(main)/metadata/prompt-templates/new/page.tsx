"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { createPromptTemplate } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus, Trash2, FileText } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

interface NewPromptTemplate {
  name: string;
  fields: string[];
  template: string;
}

export default function NewPromptTemplatePage() {
  const router = useRouter();
  const { confirm, DialogComponent } = useConfirmDialog();

  const [templateData, setTemplateData] = useState<NewPromptTemplate>({
    name: '',
    fields: [''],
    template: '',
  });

  const [saving, setSaving] = useState(false);

  // 字段数据更新处理
  const handleFieldsChange = (index: number, value: string) => {
    const updatedFields = [...templateData.fields];
    updatedFields[index] = value;

    setTemplateData(prev => ({
      ...prev,
      fields: updatedFields
    }));
  };

  // 添加新字段
  const addField = () => {
    setTemplateData(prev => ({
      ...prev,
      fields: [...prev.fields, '']
    }));
  };

  // 删除字段
  const removeField = (index: number) => {
    // 至少保留一个字段
    if (templateData.fields.length > 1) {
      const updatedFields = templateData.fields.filter((_, i) => i !== index);
      setTemplateData(prev => ({
        ...prev,
        fields: updatedFields
      }));
    }
  };

  // 验证字段配置中的占位符
  const validatePlaceholders = () => {
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

  const handleSave = async () => {
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

      const createResult = await createPromptTemplate({
        name: templateData.name,
        fields: fieldsArray,
        template: templateData.template,
      });

      toast.success('提示词模板创建成功');
      router.push(`/metadata/prompt-templates/${createResult.data.id}`);
    } catch (error) {
      console.error('Failed to create prompt template:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    confirm({
      title: "确认取消",
      description: "确定要取消创建提示词模板吗？",
      variant: "default",
      onConfirm: () => {
        router.push('/metadata/prompt-templates');
      }
    });
  };

  const handleBack = () => {
    router.push('/metadata/prompt-templates');
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
              <FileText className="h-6 w-6" />
              新建提示词模板
            </h1>
            <p className="text-muted-foreground">创建新的AI查询提示词模板和字段配置</p>
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
            {saving ? '创建中...' : '创建模板'}
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
              <div>
                <Label htmlFor="template-name">模板名称 *</Label>
                <Input
                  id="template-name"
                  value={templateData.name}
                  onChange={(e) => setTemplateData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="请输入模板名称"
                />
              </div>
            </CardContent>
          </Card>

          {/* 字段配置 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                字段配置
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addField}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  添加字段
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {templateData.fields.map((field: string, index: number) => (
                  <div key={index} className="flex gap-2 items-center">
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
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-500 mt-2">
                字段名将在模板中作为占位符使用，格式：<code className="px-1 py-0.5 bg-gray-100 rounded">{"{字段名}"}</code>。不添加字段表示模板没有参数（固定内容）。
              </p>
            </CardContent>
          </Card>

          {/* 模板内容 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">提示词模板 *</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={templateData.template}
                onChange={(e) => setTemplateData(prev => ({ ...prev, template: e.target.value }))}
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
            </CardContent>
          </Card>
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
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

          {/* 示例模板 */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-green-600 text-sm font-medium">✓</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">示例模板</h3>
                  <div className="mt-2 text-sm text-green-700 space-y-1">
                    <p className="font-mono text-xs bg-gray-50 p-2 rounded">
                      {"根据用户查询：{query}"}<br/>
                      {"在数据表 {table_name} 中查找相关信息"}
                    </p>
                  </div>
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