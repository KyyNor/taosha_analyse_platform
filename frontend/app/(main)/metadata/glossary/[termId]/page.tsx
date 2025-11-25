"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getGlossaryTermById, updateGlossaryTerm } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Edit3, Eye, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface GlossaryTerm {
  id: number;
  name: string;
  type: string;
  content: string; // 改为字符串
  creator: string;
  is_basic: boolean;
  created_at: string;
  updated_at: string;
}

const TERM_TYPES = [
  { value: "concept", label: "概念解释" },
  { value: "sql_qa", label: "SQL问答" },
  { value: "dict_mapping", label: "字典转换" },
];

export default function GlossaryTermDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const termId = params.termId as string;
  const mode = searchParams.get("mode") || "view";

  const [termData, setTermData] = useState<GlossaryTerm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 格式化JSON字符串显示
  const formatContent = (contentStr: string) => {
    try {
      if (!contentStr) return "{}";
      const parsed = JSON.parse(contentStr);
      return JSON.stringify(parsed, null, 2);
    } catch (error) {
      return contentStr; // 如果解析失败，返回原始字符串
    }
  };

  // 加载术语数据
  const loadTerm = async () => {
    setLoading(true);
    try {
      const res = await getGlossaryTermById(Number(termId));
      if (res.success) {
        setTermData(res.data);
      } else {
        toast.error("加载术语数据失败");
      }
    } catch (error) {
      console.error("Failed to load term:", error);
      toast.error("加载术语数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (termId) {
      loadTerm();
    }
  }, [termId]);

  // 数据更新处理
  const handleTermDataChange = (field: keyof GlossaryTerm, value: any) => {
    if (!termData) return;

    setTermData(prev => ({
      ...prev!,
      [field]: value
    }));
  };

  // 内容数据更新处理
  const handleContentChange = (field: string, value: any) => {
    if (!termData) return;

    const currentContent = parseContent(termData.type, termData.content);
    const updatedContent = { ...currentContent, [field]: value };

    setTermData(prev => ({
      ...prev!,
      content: JSON.stringify(updatedContent)
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!termData) return errors;

    // 验证基本信息
    if (!termData.name || termData.name.trim() === '') {
      errors.push('术语名称不能为空');
    }

    if (!termData.type) {
      errors.push('术语类型不能为空');
    }

    // 根据类型验证内容
    const content = parseContent(termData.type, termData.content);

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

  // 保存处理
  const handleSave = async () => {
    if (!termData) return;

    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      const content = parseContent(termData.type, termData.content);

      await updateGlossaryTerm(Number(termId), {
        name: termData.name,
        type: termData.type,
        content: buildContent(termData.type, content),
        is_basic: termData.is_basic,
      });

      toast.success('术语更新成功');
      if (mode === "edit") {
        router.push(`/metadata/glossary/${termId}`);
      } else {
        await loadTerm(); // 重新加载数据
      }
    } catch (error) {
      console.error('Failed to update term:', error);
      toast.error('更新失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 切换编辑模式
  const handleEdit = () => {
    router.push(`/metadata/glossary/${termId}?mode=edit`);
  };

  // 取消编辑
  const handleCancel = () => {
    if (confirm('确定要取消编辑吗？未保存的更改将丢失。')) {
      if (mode === "edit") {
        router.push(`/metadata/glossary/${termId}`);
      } else {
        router.push('/metadata/glossary');
      }
    }
  };

  // 返回列表
  const handleBack = () => {
    router.push('/metadata/glossary');
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

  if (!termData) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">术语不存在</h2>
          <p className="text-gray-600 mb-6">请检查术语ID是否正确</p>
          <Button onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回列表
          </Button>
        </div>
      </div>
    );
  }

  const content = parseContent(termData.type, termData.content);
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
              {isEditing ? "编辑术语" : "术语详情"}
            </h1>
            <p className="text-muted-foreground">
              {termData.type === "concept" && "概念解释型术语"}
              {termData.type === "sql_qa" && "SQL问答型术语"}
              {termData.type === "dict_mapping" && "字典转换型术语"}
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
                  <Label htmlFor="term-name">术语名称 *</Label>
                  {isEditing ? (
                    <Input
                      id="term-name"
                      value={termData.name}
                      onChange={(e) => handleTermDataChange('name', e.target.value)}
                      placeholder="请输入术语名称"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {termData.name}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="term-type">术语类型 *</Label>
                  {isEditing ? (
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
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {TERM_TYPES.find(t => t.value === termData.type)?.label || termData.type}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="term-basic"
                  checked={termData.is_basic}
                  onCheckedChange={(checked) => handleTermDataChange('is_basic', checked)}
                  disabled={!isEditing}
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
                  {isEditing ? (
                    <Textarea
                      id="concept-definition"
                      value={content.definition || ''}
                      onChange={(e) => handleContentChange('definition', e.target.value)}
                      placeholder="请输入概念的详细定义"
                      rows={4}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] whitespace-pre-wrap">
                      {content.definition || '暂无定义'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="concept-example">示例说明</Label>
                  {isEditing ? (
                    <Textarea
                      id="concept-example"
                      value={content.example || ''}
                      onChange={(e) => handleContentChange('example', e.target.value)}
                      placeholder="请输入具体示例帮助理解"
                      rows={3}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[80px] whitespace-pre-wrap">
                      {content.example || '暂无示例'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="concept-context">使用上下文</Label>
                  {isEditing ? (
                    <Textarea
                      id="concept-context"
                      value={content.context || ''}
                      onChange={(e) => handleContentChange('context', e.target.value)}
                      placeholder="请输入该术语的使用场景和上下文"
                      rows={3}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[80px] whitespace-pre-wrap">
                      {content.context || '暂无上下文说明'}
                    </div>
                  )}
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
                  {isEditing ? (
                    <Textarea
                      id="sql-question"
                      value={content.question || ''}
                      onChange={(e) => handleContentChange('question', e.target.value)}
                      placeholder="请输入常见的SQL相关问题"
                      rows={3}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[80px] whitespace-pre-wrap">
                      {content.question || '暂无问题'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="sql-answer">标准答案 *</Label>
                  {isEditing ? (
                    <Textarea
                      id="sql-answer"
                      value={content.answer || ''}
                      onChange={(e) => handleContentChange('answer', e.target.value)}
                      placeholder="请输入对应的标准答案"
                      rows={4}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] whitespace-pre-wrap">
                      {content.answer || '暂无答案'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="sql-template">SQL模板</Label>
                  {isEditing ? (
                    <Textarea
                      id="sql-template"
                      value={content.sql_template || ''}
                      onChange={(e) => handleContentChange('sql_template', e.target.value)}
                      placeholder="请输入相关的SQL查询模板（可选）"
                      rows={4}
                      className="font-mono text-sm"
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] font-mono text-sm whitespace-pre-wrap">
                      {content.sql_template || '暂无SQL模板'}
                    </div>
                  )}
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
                    {isEditing ? (
                      <Input
                        id="dict-source"
                        value={content.source_value || ''}
                        onChange={(e) => handleContentChange('source_value', e.target.value)}
                        placeholder="请输入源值"
                      />
                    ) : (
                      <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                        {content.source_value || '暂无源值'}
                      </div>
                    )}
                  </div>
                  <div>
                    <Label htmlFor="dict-target">目标值 *</Label>
                    {isEditing ? (
                      <Input
                        id="dict-target"
                        value={content.target_value || ''}
                        onChange={(e) => handleContentChange('target_value', e.target.value)}
                        placeholder="请输入目标值"
                      />
                    ) : (
                      <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                        {content.target_value || '暂无目标值'}
                      </div>
                    )}
                  </div>
                </div>
                <div>
                  <Label htmlFor="dict-description">转换说明</Label>
                  {isEditing ? (
                    <Textarea
                      id="dict-description"
                      value={content.description || ''}
                      onChange={(e) => handleContentChange('description', e.target.value)}
                      placeholder="请输入转换规则的说明和用途"
                      rows={3}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[80px] whitespace-pre-wrap">
                      {content.description || '暂无说明'}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
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
                <Label className="text-sm font-medium text-gray-700">术语ID</Label>
                <div className="mt-1 text-sm text-gray-900">{termData.id}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">创建者</Label>
                <div className="mt-1 text-sm text-gray-900">{termData.creator || '-'}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">创建时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(termData.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">更新时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(termData.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 操作说明 */}
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
        </div>
      </div>
    </div>
  );
}