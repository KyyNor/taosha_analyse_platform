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

interface NewGlossaryTerm {
  name: string;
  type: string;
  content: TermContent;
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
    content: {
      content: '',
      question: '',
      answer: '',
      remark: '',
      col_name: '',
      dict_map: []
    },
    is_basic: false,
  });

  const [saving, setSaving] = useState(false);

  // 术语数据更新处理
  const handleTermDataChange = (field: keyof NewGlossaryTerm, value: any) => {
    setTermData(prev => {
      const updated = { ...prev, [field]: value };
      return updated;
    });
  };

  // 内容字段更新处理
  const handleContentChange = (field: keyof TermContent, value: any) => {
    setTermData(prev => ({
      ...prev,
      content: {
        ...prev.content,
        [field]: value
      }
    }));
  };

  // 字典映射项操作
  const addMapping = () => {
    handleContentChange('dict_map', [...termData.content.dict_map, { key: '', value: '' }]);
  };

  const removeMapping = (index: number) => {
    const newDictMap = termData.content.dict_map.filter((_, i) => i !== index);
    handleContentChange('dict_map', newDictMap);
  };

  const updateMapping = (index: number, field: 'key' | 'value', value: string) => {
    const newDictMap = [...termData.content.dict_map];
    newDictMap[index] = { ...newDictMap[index], [field]: value };
    handleContentChange('dict_map', newDictMap);
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
    switch (termData.type) {
      case 'concept':
        if (!termData.content.content || termData.content.content.trim() === '') {
          errors.push('概念解释内容不能为空');
        }
        break;
      case 'sql_qa':
        if (!termData.content.question || termData.content.question.trim() === '') {
          errors.push('SQL问题不能为空');
        }
        if (!termData.content.answer || termData.content.answer.trim() === '') {
          errors.push('SQL答案不能为空');
        }
        break;
      case 'dict_mapping':
        if (!termData.content.col_name || termData.content.col_name.trim() === '') {
          errors.push('字段名称不能为空');
        }
        if (termData.content.dict_map.length === 0) {
          errors.push('至少需要添加一个字典映射项');
        }
        // 验证映射项是否都填写完整
        const hasIncompleteMapping = termData.content.dict_map.some(
          mapping => !mapping.key.trim() || !mapping.value.trim()
        );
        if (hasIncompleteMapping) {
          errors.push('字典映射项中的键和值都不能为空');
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
      // 构建最终的内容
      const createResult = await createGlossaryTerm({
        name: termData.name,
        type: termData.type,
        content: termData.content,
        creator: "系统用户", // 可以从用户上下文获取
        is_basic: termData.is_basic,
      });

      if (createResult.success) {
        toast.success('术语创建成功');
        router.push(`/metadata/glossary/${createResult.data.id}`);
      } else {
        throw new Error(createResult.message || '创建失败');
      }
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

          {/* 术语内容编辑区域 */}
          {termData.type === "concept" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">概念解释内容</CardTitle>
                <p className="text-sm text-muted-foreground">请输入术语的详细解释和定义</p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="concept-content">内容说明 *</Label>
                  <Textarea
                    id="concept-content"
                    value={termData.content.content}
                    onChange={(e) => handleContentChange('content', e.target.value)}
                    placeholder="请输入概念的详细解释，例如：月日均大于1000元的存款账户"
                    rows={4}
                  />
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
                  <Textarea
                    id="sql-question"
                    value={termData.content.question}
                    onChange={(e) => handleContentChange('question', e.target.value)}
                    placeholder="请输入常见的SQL相关问题，例如：如何查看用户的基本信息？"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="sql-answer">答案 *</Label>
                  <Textarea
                    id="sql-answer"
                    value={termData.content.answer}
                    onChange={(e) => handleContentChange('answer', e.target.value)}
                    placeholder="请输入对应的标准答案，可以包含SQL语句和详细说明"
                    rows={4}
                    className="font-mono text-sm"
                  />
                </div>
                <div>
                  <Label htmlFor="sql-remark">备注</Label>
                  <Input
                    id="sql-remark"
                    value={termData.content.remark}
                    onChange={(e) => handleContentChange('remark', e.target.value)}
                    placeholder="请输入备注信息（可选）"
                  />
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
                  <Input
                    id="dict-colname"
                    value={termData.content.col_name}
                    onChange={(e) => handleContentChange('col_name', e.target.value)}
                    placeholder="请输入字段名称，多个字段用逗号分隔，例如：tran_code,fund_tran_code"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    多个字段名请用英文逗号分隔
                  </p>
                </div>
                <div>
                  <Label>键值映射 *</Label>
                  <div className="border rounded-lg p-4 space-y-3">
                    {termData.content.dict_map.map((mapping, index) => (
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
                          <Plus className="h-3 w-3 rotate-45" />
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
                  <p className="text-xs text-muted-foreground mt-1">
                    至少需要添加一个有效的键值映射
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {termData.type === "" && (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-8 text-muted-foreground">
                  <Plus className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>请先选择术语类型以显示对应的输入表单</p>
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