"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createGlossaryTerm } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus } from "lucide-react";
import { toast } from "sonner";

interface NewGlossaryTerm {
  name: string;
  type: string;
  content: any;
  is_basic: boolean;
}

const TERM_TYPES = [
  { value: "concept", label: "概念解释" },
  { value: "sql_qa", label: "SQL问答" },
  { value: "dict_mapping", label: "字典转换" },
];

export default function NewGlossaryTermPage() {
  const router = useRouter();

  const [termData, setTermData] = useState<NewGlossaryTerm>({
    name: '',
    type: '',
    content: {},
    is_basic: false,
  });

  const [saving, setSaving] = useState(false);

  // 根据类型构建内容
  const buildContent = (type: string) => {
    switch (type) {
      case "concept":
        return {
          definition: "",
          example: "",
          context: "",
        };
      case "sql_qa":
        return {
          question: "",
          answer: "",
          sql_template: "",
        };
      case "dict_mapping":
        return {
          source_value: "",
          target_value: "",
          description: "",
        };
      default:
        return {};
    }
  };

  // 术语数据更新处理
  const handleTermDataChange = (field: keyof NewGlossaryTerm, value: any) => {
    setTermData(prev => {
      const updated = { ...prev, [field]: value };

      // 如果类型发生变化，重置内容
      if (field === 'type' && value !== prev.type) {
        updated.content = buildContent(value);
      }

      return updated;
    });
  };

  // 内容数据更新处理
  const handleContentChange = (field: string, value: any) => {
    setTermData(prev => ({
      ...prev,
      content: {
        ...prev.content,
        [field]: value
      }
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证基本信息
    if (!termData.name || termData.name.trim() === '') {
      errors.push('术语名称不能为空');
    }

    if (!termData.type) {
      errors.push('术语类型不能为空');
    }

    // 根据类型验证内容
    const content = termData.content;

    switch (termData.type) {
      case "concept":
        if (!content.definition || content.definition.trim() === '') {
          errors.push('概念定义不能为空');
        }
        break;
      case "sql_qa":
        if (!content.question || content.question.trim() === '') {
          errors.push('SQL问题不能为空');
        }
        if (!content.answer || content.answer.trim() === '') {
          errors.push('SQL答案不能为空');
        }
        break;
      case "dict_mapping":
        if (!content.source_value || content.source_value.trim() === '') {
          errors.push('源值不能为空');
        }
        if (!content.target_value || content.target_value.trim() === '') {
          errors.push('目标值不能为空');
        }
        break;
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
      const createResult = await createGlossaryTerm({
        name: termData.name,
        type: termData.type,
        content: termData.content,
        creator: "系统用户", // 可以从用户上下文获取
        is_basic: termData.is_basic,
      });

      toast.success('术语创建成功');
      router.push(`/metadata/glossary/${createResult.data.id}`);
    } catch (error) {
      console.error('Failed to create term:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (confirm('确定要取消创建术语吗？')) {
      router.push('/metadata/glossary');
    }
  };

  const handleBack = () => {
    router.push('/metadata/glossary');
  };

  const content = termData.content;

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
              <Plus className="h-6 w-6" />
              新建术语
            </h1>
            <p className="text-muted-foreground">创建新的业务术语和内容定义</p>
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
            {saving ? '创建中...' : '创建术语'}
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
                  <Label htmlFor="term-name">术语名称 *</Label>
                  <Input
                    id="term-name"
                    value={termData.name}
                    onChange={(e) => handleTermDataChange('name', e.target.value)}
                    placeholder="请输入术语名称"
                  />
                </div>
                <div>
                  <Label htmlFor="term-type">术语类型 *</Label>
                  <Select
                    value={termData.type}
                    onValueChange={(value) => handleTermDataChange('type', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择术语类型" />
                    </SelectTrigger>
                    <SelectContent>
                      {TERM_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="term-basic"
                  checked={termData.is_basic}
                  onCheckedChange={(checked) => handleTermDataChange('is_basic', checked)}
                />
                <Label htmlFor="term-basic">基础术语</Label>
              </div>
            </CardContent>
          </Card>

          {/* 根据类型显示不同的内容编辑区域 */}
          {termData.type === "concept" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">概念解释内容</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="concept-definition">概念定义 *</Label>
                  <Textarea
                    id="concept-definition"
                    value={content.definition || ''}
                    onChange={(e) => handleContentChange('definition', e.target.value)}
                    placeholder="请输入概念的详细定义"
                    rows={4}
                  />
                </div>
                <div>
                  <Label htmlFor="concept-example">示例说明</Label>
                  <Textarea
                    id="concept-example"
                    value={content.example || ''}
                    onChange={(e) => handleContentChange('example', e.target.value)}
                    placeholder="请输入具体示例帮助理解"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="concept-context">使用上下文</Label>
                  <Textarea
                    id="concept-context"
                    value={content.context || ''}
                    onChange={(e) => handleContentChange('context', e.target.value)}
                    placeholder="请输入该术语的使用场景和上下文"
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {termData.type === "sql_qa" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">SQL问答内容</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="sql-question">常见问题 *</Label>
                  <Textarea
                    id="sql-question"
                    value={content.question || ''}
                    onChange={(e) => handleContentChange('question', e.target.value)}
                    placeholder="请输入常见的SQL相关问题"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="sql-answer">标准答案 *</Label>
                  <Textarea
                    id="sql-answer"
                    value={content.answer || ''}
                    onChange={(e) => handleContentChange('answer', e.target.value)}
                    placeholder="请输入对应的标准答案"
                    rows={4}
                  />
                </div>
                <div>
                  <Label htmlFor="sql-template">SQL模板</Label>
                  <Textarea
                    id="sql-template"
                    value={content.sql_template || ''}
                    onChange={(e) => handleContentChange('sql_template', e.target.value)}
                    placeholder="请输入相关的SQL查询模板（可选）"
                    rows={4}
                    className="font-mono text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {termData.type === "dict_mapping" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">字典转换内容</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="dict-source">源值 *</Label>
                    <Input
                      id="dict-source"
                      value={content.source_value || ''}
                      onChange={(e) => handleContentChange('source_value', e.target.value)}
                      placeholder="请输入源值"
                    />
                  </div>
                  <div>
                    <Label htmlFor="dict-target">目标值 *</Label>
                    <Input
                      id="dict-target"
                      value={content.target_value || ''}
                      onChange={(e) => handleContentChange('target_value', e.target.value)}
                      placeholder="请输入目标值"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="dict-description">转换说明</Label>
                  <Textarea
                    id="dict-description"
                    value={content.description || ''}
                    onChange={(e) => handleContentChange('description', e.target.value)}
                    placeholder="请输入转换规则的说明和用途"
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
          {/* 术语类型说明 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">术语类型说明</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p><strong>概念解释：</strong>用于定义业务术语的含义和用法</p>
                    <p><strong>SQL问答：</strong>存储常见SQL问题和标准答案</p>
                    <p><strong>字典转换：</strong>定义值之间的映射转换关系</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 创建提示 */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-green-600 text-sm font-medium">✓</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">创建提示</h3>
                  <p className="mt-1 text-sm text-green-700">
                    术语创建后可以在智能查询中提供更好的上下文理解和答案生成支持。
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