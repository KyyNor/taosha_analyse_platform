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
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

// 字典映射项接口
interface DictMapping {
  key: string;
  value: string;
}

// 术语内容接口
interface TermContent {
  content: string;        // 通用内容（概念解释使用）
  question: string;       // SQL问题
  answer: string;         // SQL答案
  remark: string;         // 备注说明
  col_name: string;       // 字段名称
  dict_map: DictMapping[]; // 字典映射
}

interface GlossaryTerm {
  id: number;
  name: string;
  type: string;
  content: string; // JSON字符串
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
  const { confirm, DialogComponent } = useConfirmDialog();

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

  // 解析内容
  const parseContent = (type: string, content: any): TermContent => {
    if (typeof content === 'string') {
      try {
        const parsed = JSON.parse(content);
        // 确保返回的对象包含所有必需字段
        return {
          content: parsed.content || '',
          question: parsed.question || '',
          answer: parsed.answer || '',
          remark: parsed.remark || '',
          col_name: parsed.col_name || '',
          dict_map: parsed.dict_map || []
        };
      } catch {
        // 解析失败时返回默认空对象
        return {
          content: '',
          question: '',
          answer: '',
          remark: '',
          col_name: '',
          dict_map: []
        };
      }
    }
    // 如果已经是对象，确保包含所有字段
    return {
      content: content.content || '',
      question: content.question || '',
      answer: content.answer || '',
      remark: content.remark || '',
      col_name: content.col_name || '',
      dict_map: content.dict_map || []
    };
  };

  // 构建内容
  const buildContent = (type: string, content: any) => {
    return content;
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

  // 字典映射项操作
  const addMapping = () => {
    if (!termData) return;
    const currentContent = parseContent(termData.type, termData.content);
    handleContentChange('dict_map', [...currentContent.dict_map, { key: '', value: '' }]);
  };

  const removeMapping = (index: number) => {
    if (!termData) return;
    const currentContent = parseContent(termData.type, termData.content);
    const newDictMap = currentContent.dict_map.filter((_, i) => i !== index);
    handleContentChange('dict_map', newDictMap);
  };

  const updateMapping = (index: number, field: 'key' | 'value', value: string) => {
    if (!termData) return;
    const currentContent = parseContent(termData.type, termData.content);
    const newDictMap = [...currentContent.dict_map];
    newDictMap[index] = { ...newDictMap[index], [field]: value };
    handleContentChange('dict_map', newDictMap);
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
      case 'concept':
        if (!content.content || content.content.trim() === '') {
          errors.push('概念解释内容不能为空');
        }
        break;
      case 'sql_qa':
        if (!content.question || content.question.trim() === '') {
          errors.push('SQL问题不能为空');
        }
        if (!content.answer || content.answer.trim() === '') {
          errors.push('SQL答案不能为空');
        }
        break;
      case 'dict_mapping':
        if (!content.col_name || content.col_name.trim() === '') {
          errors.push('字段名称不能为空');
        }
        if (content.dict_map.length === 0) {
          errors.push('至少需要添加一个字典映射项');
        }
        // 验证映射项是否都填写完整
        const hasIncompleteMapping = content.dict_map.some(
          mapping => !mapping.key.trim() || !mapping.value.trim()
        );
        if (hasIncompleteMapping) {
          errors.push('字典映射项中的键和值都不能为空');
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
    confirm({
      title: "确认取消",
      description: "确定要取消编辑吗？未保存的更改将丢失。",
      variant: "default",
      onConfirm: () => {
        if (mode === "edit") {
          router.push(`/metadata/glossary/${termId}`);
        } else {
          router.push('/metadata/glossary');
        }
      }
    });
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
                <p className="text-sm text-muted-foreground">请输入术语的详细解释和定义</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="concept-content">内容说明 *</Label>
                  {isEditing ? (
                    <Textarea
                      id="concept-content"
                      value={content.content || ''}
                      onChange={(e) => handleContentChange('content', e.target.value)}
                      placeholder="请输入概念的详细解释，例如：月日均大于1000元的存款账户"
                      rows={4}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] whitespace-pre-wrap">
                      {content.content || '暂无内容'}
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
                <p className="text-sm text-muted-foreground">请配置常见的SQL问题和标准答案</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="sql-question">问题 *</Label>
                  {isEditing ? (
                    <Textarea
                      id="sql-question"
                      value={content.question || ''}
                      onChange={(e) => handleContentChange('question', e.target.value)}
                      placeholder="请输入常见的SQL相关问题，例如：如何查看用户的基本信息？"
                      rows={3}
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[80px] whitespace-pre-wrap">
                      {content.question || '暂无问题'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="sql-answer">答案 *</Label>
                  {isEditing ? (
                    <Textarea
                      id="sql-answer"
                      value={content.answer || ''}
                      onChange={(e) => handleContentChange('answer', e.target.value)}
                      placeholder="请输入对应的标准答案，可以包含SQL语句和详细说明"
                      rows={4}
                      className="font-mono text-sm"
                    />
                  ) : (
                    <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] font-mono text-sm whitespace-pre-wrap">
                      {content.answer || '暂无答案'}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="sql-remark">备注</Label>
                  {isEditing ? (
                    <Input
                      id="sql-remark"
                      value={content.remark || ''}
                      onChange={(e) => handleContentChange('remark', e.target.value)}
                      placeholder="请输入备注信息（可选）"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {content.remark || '暂无备注'}
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
                <p className="text-sm text-muted-foreground">请配置字段值的映射转换关系</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="dict-colname">字段名称 *</Label>
                  {isEditing ? (
                    <>
                      <Input
                        id="dict-colname"
                        value={content.col_name || ''}
                        onChange={(e) => handleContentChange('col_name', e.target.value)}
                        placeholder="请输入字段名称，多个字段用逗号分隔，例如：tran_code,fund_tran_code"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        多个字段名请用英文逗号分隔
                      </p>
                    </>
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {content.col_name || '暂无字段名称'}
                    </div>
                  )}
                </div>
                <div>
                  <Label>键值映射 *</Label>
                  {isEditing ? (
                    <div className="border rounded-lg p-4 space-y-3">
                      {content.dict_map.map((mapping, index) => (
                        <div key={index} className="flex gap-3 items-center">
                          <div className="flex-1">
                            <Input
                              value={mapping.key}
                              onChange={(e) => updateMapping(index, 'key', e.target.value)}
                              placeholder="原值"
                              className="font-mono text-sm"
                            />
                          </div>
                          <div className="text-muted-foreground">→</div>
                          <div className="flex-1">
                            <Input
                              value={mapping.value}
                              onChange={(e) => updateMapping(index, 'value', e.target.value)}
                              placeholder="映射值"
                              className="font-mono text-sm"
                            />
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeMapping(index)}
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                      <div className="pt-3 border-t">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={addMapping}
                          className="w-full"
                        >
                          <Plus className="h-3 w-3 mr-1" />
                          添加映射项
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-1 border rounded-lg p-4 space-y-2">
                      {content.dict_map.length > 0 ? (
                        content.dict_map.map((mapping, index) => (
                          <div key={index} className="flex gap-3 items-center p-2 bg-gray-50 rounded">
                            <div className="flex-1 font-mono text-sm">
                              {mapping.key}
                            </div>
                            <div className="text-muted-foreground">→</div>
                            <div className="flex-1 font-mono text-sm">
                              {mapping.value}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center text-muted-foreground py-4">
                          暂无映射项
                        </div>
                      )}
                    </div>
                  )}
                  {isEditing && (
                    <p className="text-xs text-muted-foreground mt-1">
                      至少需要添加一个有效的键值映射
                    </p>
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
      <DialogComponent />
    </div>
  );
}