"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { createDocument } from "@/lib/services/knowledgeService";
import { ArrowLeft, Save, X, Plus, FileText, FileCode } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

interface NewDocumentData {
  title: string;
  source_type: 'file' | 'text' | 'sql';
  source_path: string;
  raw_content: string;
}

const SOURCE_TYPES = [
  { value: 'file', label: '文件', description: '从文件路径读取文档内容' },
  { value: 'text', label: '文本', description: '直接输入文本内容' },
  { value: 'sql', label: 'SQL文件', description: '从SQL脚本文件提取知识' }
];

export default function NewDocumentPage() {
  const router = useRouter();
  const { confirm, DialogComponent } = useConfirmDialog();

  const [documentData, setDocumentData] = useState<NewDocumentData>({
    title: '',
    source_type: 'text',
    source_path: '',
    raw_content: ''
  });

  const [saving, setSaving] = useState(false);

  // 文档数据更新处理
  const handleDocumentDataChange = (field: keyof NewDocumentData, value: string) => {
    setDocumentData(prev => ({ ...prev, [field]: value }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!documentData.title || documentData.title.trim() === '') {
      errors.push('文档标题不能为空');
    }

    if (!documentData.source_type) {
      errors.push('源类型不能为空');
    }

    // 根据源类型验证输入
    if (documentData.source_type === 'file' || documentData.source_type === 'sql') {
      if (!documentData.source_path || documentData.source_path.trim() === '') {
        errors.push('文件路径不能为空');
      }
    } else if (documentData.source_type === 'text') {
      if (!documentData.raw_content || documentData.raw_content.trim() === '') {
        errors.push('文本内容不能为空');
      }
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
      const createData: any = {
        title: documentData.title,
        source_type: documentData.source_type
      };

      // 根据源类型添加相应字段
      if (documentData.source_type === 'file' || documentData.source_type === 'sql') {
        createData.source_path = documentData.source_path;
      } else if (documentData.source_type === 'text') {
        createData.raw_content = documentData.raw_content;
      }

      const result = await createDocument(createData);

      if (result.id) {
        toast.success('文档创建成功');
        router.push(`/metadata/knowledge/${result.id}`);
      } else {
        throw new Error('创建失败');
      }
    } catch (error: any) {
      console.error('Failed to create document:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '创建失败，请重试';
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    confirm({
      title: "确认取消",
      description: "确定要取消创建文档吗？",
      variant: "default",
      onConfirm: () => {
        router.push('/metadata/knowledge');
      }
    });
  };

  const handleBack = () => {
    router.push('/metadata/knowledge');
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
              新建知识文档
            </h1>
            <p className="text-muted-foreground">创建新的知识文档，支持文件、文本和SQL脚本</p>
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
            {saving ? '创建中...' : '创建文档'}
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
                <Label htmlFor="doc-title">文档标题 *</Label>
                <Input
                  id="doc-title"
                  value={documentData.title}
                  onChange={(e) => handleDocumentDataChange('title', e.target.value)}
                  placeholder="请输入文档标题"
                />
              </div>
              <div>
                <Label htmlFor="doc-type">源类型 *</Label>
                <Select
                  value={documentData.source_type}
                  onValueChange={(value: 'file' | 'text' | 'sql') => handleDocumentDataChange('source_type', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择源类型" />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCE_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  {SOURCE_TYPES.find(t => t.value === documentData.source_type)?.description}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* 源类型特定内容 */}
          {(documentData.source_type === 'file' || documentData.source_type === 'sql') && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  {documentData.source_type === 'file' ? (
                    <>
                      <FileText className="h-5 w-5" />
                      文件路径
                    </>
                  ) : (
                    <>
                      <FileCode className="h-5 w-5" />
                      SQL文件路径
                    </>
                  )}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {documentData.source_type === 'file'
                    ? '请提供文件的绝对路径，系统将自动读取文件内容'
                    : '请提供SQL脚本的绝对路径，系统将从SQL中提取知识'}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="doc-path">文件路径 *</Label>
                  <Input
                    id="doc-path"
                    value={documentData.source_path}
                    onChange={(e) => handleDocumentDataChange('source_path', e.target.value)}
                    placeholder={documentData.source_type === 'file'
                      ? '/path/to/your/document.txt'
                      : '/path/to/your/script.sql'}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    请输入绝对路径，例如: /home/user/data/document.txt
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {documentData.source_type === 'text' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  文本内容
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  请直接输入或粘贴文本内容
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="doc-content">内容 *</Label>
                  <Textarea
                    id="doc-content"
                    value={documentData.raw_content}
                    onChange={(e) => handleDocumentDataChange('raw_content', e.target.value)}
                    placeholder="请输入文档内容..."
                    rows={12}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    支持长文本输入，建议分段落以提高知识提取效果
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
          {/* 源类型说明 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">源类型说明</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p><strong>文件：</strong>从服务器文件系统读取文档内容</p>
                    <p><strong>文本：</strong>直接输入或粘贴文本内容</p>
                    <p><strong>SQL：</strong>从SQL脚本中提取表结构和业务逻辑知识</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 后续步骤 */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-green-600 text-sm font-medium">✓</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-800">后续步骤</h3>
                  <p className="mt-1 text-sm text-green-700">
                    文档创建后，您可以使用LLM自动生成知识片段，或基于特定主题提取知识。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 提示信息 */}
          <Card className="border-l-4 border-l-yellow-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                    <span className="text-yellow-600 text-sm font-medium">!</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-yellow-800">注意事项</h3>
                  <p className="mt-1 text-sm text-yellow-700">
                    文件路径必须是服务器可访问的绝对路径。文本内容建议分段落，以提高知识片段生成的质量。
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
