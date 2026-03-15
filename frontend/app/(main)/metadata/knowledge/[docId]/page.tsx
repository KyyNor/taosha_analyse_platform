"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  getDocumentById,
  deleteDocument,
  generateFragments,
  extractByTopic,
  saveFragments,
  updateFragment,
  deleteFragment,
  type KnowledgeDocumentDetail,
  type KnowledgeFragment
} from "@/lib/services/knowledgeService";
import { ArrowLeft, Save, Trash2, Sparkles, Search, Check, FileText } from "lucide-react";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";
import { documentSourceTypeBadgeConfig, documentProcessingStatusBadgeConfig } from "@/lib/utils/badgeConfigs";

export default function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const docId = parseInt(params?.docId as string);
  const { confirm, DialogComponent } = useConfirmDialog();

  const [document, setDocument] = useState<KnowledgeDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // LLM生成状态
  const [fragmentCount, setFragmentCount] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [candidateFragments, setCandidateFragments] = useState<KnowledgeFragment[]>([]);

  // 主题提取状态
  const [extractionTheme, setExtractionTheme] = useState('');
  const [extractionPrompt, setExtractionPrompt] = useState('');
  const [extracting, setExtracting] = useState(false);

  // 片段选择状态
  const [selectedFragmentIds, setSelectedFragmentIds] = useState<Set<number>>([]);
  const [savingFragments, setSavingFragments] = useState(false);

  // 片段编辑状态
  const [editingFragment, setEditingFragment] = useState<KnowledgeFragment | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  // 片段删除状态
  const [deletingFragmentId, setDeletingFragmentId] = useState<number | null>(null);

  useEffect(() => {
    loadDocument();
  }, [docId]);

  const loadDocument = async () => {
    setLoading(true);
    try {
      const data = await getDocumentById(docId);
      setDocument(data);
    } catch (error) {
      console.error('Failed to load document:', error);
      toast.error('加载文档失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    confirm({
      title: "确认删除",
      description: `确定要删除文档"${document?.title}"吗？删除后无法恢复，其关联的所有片段也将被删除。`,
      variant: "destructive",
      onConfirm: async () => {
        try {
          await deleteDocument(docId);
          toast.success('文档删除成功');
          router.push('/metadata/knowledge');
        } catch (error) {
          console.error('Failed to delete document:', error);
          toast.error('删除失败，请重试');
        }
      }
    });
  };

  const handleBack = () => {
    router.push('/metadata/knowledge');
  };

  // LLM自动生成片段
  const handleGenerateFragments = async () => {
    if (fragmentCount < 1 || fragmentCount > 20) {
      toast.error('片段数量必须在1-20之间');
      return;
    }

    setGenerating(true);
    try {
      const result = await generateFragments(docId, fragmentCount);
      // 为新片段添加临时ID（负数，用于区分）
      const newFragments = result.fragments.map((frag, idx) => ({
        ...frag,
        id: -(candidateFragments.length + idx + 1)
      }));
      setCandidateFragments(prev => [...prev, ...newFragments]);
      toast.success(`成功生成${result.total_count}个片段`);
    } catch (error: any) {
      console.error('Failed to generate fragments:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '生成片段失败';
      toast.error(errorMessage);
    } finally {
      setGenerating(false);
    }
  };

  // 主题提取
  const handleExtractByTopic = async () => {
    if (!extractionTheme.trim() || !extractionPrompt.trim()) {
      toast.error('提取主题和提取逻辑不能为空');
      return;
    }

    setExtracting(true);
    try {
      const result = await extractByTopic(docId, extractionTheme, extractionPrompt);
      // 为新片段添加临时ID
      const newFragments = result.fragments.map((frag, idx) => ({
        ...frag,
        id: -(candidateFragments.length + idx + 1)
      }));
      setCandidateFragments(prev => [...prev, ...newFragments]);
      toast.success('主题提取成功');
      // 清空输入
      setExtractionTheme('');
      setExtractionPrompt('');
    } catch (error: any) {
      console.error('Failed to extract by topic:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '主题提取失败';
      toast.error(errorMessage);
    } finally {
      setExtracting(false);
    }
  };

  // 选中/取消选中片段
  const handleToggleFragmentSelection = (fragmentId: number) => {
    setSelectedFragmentIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fragmentId)) {
        newSet.delete(fragmentId);
      } else {
        newSet.add(fragmentId);
      }
      return newSet;
    });
  };

  // 全选/取消全选
  const handleToggleSelectAll = () => {
    if (selectedFragmentIds.size === candidateFragments.length) {
      setSelectedFragmentIds(new Set());
    } else {
      setSelectedFragmentIds(new Set(candidateFragments.map(f => f.id!)));
    }
  };

  // 编辑片段
  const handleEditFragment = (fragment: KnowledgeFragment, index: number) => {
    setEditingFragment({ ...fragment });
    setEditingIndex(index);
  };

  // 保存片段编辑
  const handleSaveFragmentEdit = () => {
    if (editingFragment && editingIndex !== null) {
      setCandidateFragments(prev => {
        const newFragments = [...prev];
        newFragments[editingIndex] = editingFragment;
        return newFragments;
      });
      setEditingFragment(null);
      setEditingIndex(null);
      toast.success('片段编辑已暂存，请点击"保存选中片段"提交到数据库');
    }
  };

  // 取消片段编辑
  const handleCancelFragmentEdit = () => {
    setEditingFragment(null);
    setEditingIndex(null);
  };

  // 删除候选片段
  const handleRemoveCandidateFragment = (fragmentId: number) => {
    setCandidateFragments(prev => prev.filter(f => f.id !== fragmentId));
    setSelectedFragmentIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(fragmentId);
      return newSet;
    });
    toast.success('片段已移除');
  };

  // 保存选中的片段到数据库
  const handleSaveSelectedFragments = async () => {
    if (selectedFragmentIds.size === 0) {
      toast.error('请至少选择一个片段');
      return;
    }

    setSavingFragments(true);
    try {
      const fragmentsToSave = candidateFragments.filter(f => selectedFragmentIds.has(f.id!));
      // 移除临时ID
      const fragmentsData = fragmentsToSave.map(({ id, ...rest }) => rest);

      await saveFragments(docId, fragmentsData);

      toast.success(`成功保存${fragmentsToSave.length}个片段`);

      // 清空候选片段和选中状态
      setCandidateFragments([]);
      setSelectedFragmentIds(new Set());

      // 刷新文档详情
      loadDocument();
    } catch (error: any) {
      console.error('Failed to save fragments:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '保存片段失败';
      toast.error(errorMessage);
    } finally {
      setSavingFragments(false);
    }
  };

  // 删除已保存的片段
  const handleDeleteSavedFragment = (fragmentId: number) => {
    confirm({
      title: "确认删除片段",
      description: "确定要删除该片段吗？",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await deleteFragment(fragmentId);
          toast.success('片段删除成功');
          loadDocument();
        } catch (error) {
          console.error('Failed to delete fragment:', error);
          toast.error('删除片段失败');
        }
      }
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center text-muted-foreground">文档不存在</div>
      </div>
    );
  }

  const sourceTypeBadge = documentSourceTypeBadgeConfig[document.source_type];
  const statusBadge = documentProcessingStatusBadgeConfig[document.processing_status];

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
              {document.title}
            </h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant={sourceTypeBadge?.variant || "default"}>
                {sourceTypeBadge?.label || document.source_type}
              </Badge>
              <Badge variant={statusBadge?.variant || "default"}>
                {statusBadge?.label || document.processing_status}
              </Badge>
              <span>•</span>
              <span>{document.fragment_count} 个片段</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            删除文档
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主要内容 */}
        <div className="lg:col-span-2 space-y-6">
          {/* LLM自动生成片段 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-500" />
                LLM自动生成片段
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <Label htmlFor="fragment-count">生成片段数量</Label>
                  <Input
                    id="fragment-count"
                    type="number"
                    min={1}
                    max={20}
                    value={fragmentCount}
                    onChange={(e) => setFragmentCount(parseInt(e.target.value) || 5)}
                    className="w-32"
                  />
                </div>
                <Button
                  onClick={handleGenerateFragments}
                  disabled={generating}
                  className="mt-6"
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  {generating ? '生成中...' : '生成片段'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 主题提取 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Search className="h-5 w-5 text-blue-500" />
                主题提取
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="extraction-theme">提取主题 *</Label>
                <Input
                  id="extraction-theme"
                  value={extractionTheme}
                  onChange={(e) => setExtractionTheme(e.target.value)}
                  placeholder="例如：存款账户相关的业务规则"
                />
              </div>
              <div>
                <Label htmlFor="extraction-prompt">提取逻辑描述 *</Label>
                <Textarea
                  id="extraction-prompt"
                  value={extractionPrompt}
                  onChange={(e) => setExtractionPrompt(e.target.value)}
                  placeholder="描述你希望提取什么样的知识，例如：提取存款账户的开户条件、账户类型、利率规则等信息"
                  rows={3}
                />
              </div>
              <Button
                onClick={handleExtractByTopic}
                disabled={extracting}
              >
                <Search className="h-4 w-4 mr-2" />
                {extracting ? '提取中...' : '提取知识'}
              </Button>
            </CardContent>
          </Card>

          {/* 候选片段列表 */}
          {candidateFragments.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">
                    候选片段 ({candidateFragments.length})
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={handleToggleSelectAll}>
                      {selectedFragmentIds.size === candidateFragments.length ? '取消全选' : '全选'}
                    </Button>
                    <Button
                      onClick={handleSaveSelectedFragments}
                      disabled={savingFragments || selectedFragmentIds.size === 0}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {savingFragments ? '保存中...' : `保存选中 (${selectedFragmentIds.size})`}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {candidateFragments.map((fragment, index) => {
                  const isSelected = selectedFragmentIds.has(fragment.id!);
                  const isEditing = editingIndex === index;

                  return (
                    <Card key={fragment.id} className={`border ${isSelected ? 'border-primary' : ''}`}>
                      <CardContent className="pt-4">
                        <div className="flex items-start gap-3">
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => handleToggleFragmentSelection(fragment.id!)}
                            className="mt-1"
                          />
                          <div className="flex-1 space-y-2">
                            {isEditing ? (
                              <>
                                <Input
                                  value={editingFragment?.title || ''}
                                  onChange={(e) => setEditingFragment(prev => prev ? { ...prev, title: e.target.value } : null)}
                                  placeholder="片段标题"
                                />
                                <Textarea
                                  value={editingFragment?.content || ''}
                                  onChange={(e) => setEditingFragment(prev => prev ? { ...prev, content: e.target.value } : null)}
                                  placeholder="片段内容"
                                  rows={4}
                                  className="text-sm"
                                />
                                <Input
                                  value={editingFragment?.summary || ''}
                                  onChange={(e) => setEditingFragment(prev => prev ? { ...prev, summary: e.target.value } : null)}
                                  placeholder="简短摘要（可选）"
                                />
                                <div className="flex gap-2">
                                  <Button size="sm" onClick={handleSaveFragmentEdit}>
                                    <Check className="h-3 w-3 mr-1" />
                                    确认
                                  </Button>
                                  <Button size="sm" variant="outline" onClick={handleCancelFragmentEdit}>
                                    取消
                                  </Button>
                                </div>
                              </>
                            ) : (
                              <>
                                <div className="flex items-start justify-between">
                                  <h4 className="font-medium">{fragment.title}</h4>
                                  <div className="flex gap-1">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleEditFragment(fragment, index)}
                                    >
                                      编辑
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleRemoveCandidateFragment(fragment.id!)}
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </div>
                                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{fragment.content}</p>
                                {fragment.summary && (
                                  <p className="text-xs text-muted-foreground italic">{fragment.summary}</p>
                                )}
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="text-xs">
                                    {fragment.generation_method === 'auto' ? '自动生成' :
                                     fragment.generation_method === 'user_extraction' ? '主题提取' : '手动创建'}
                                  </Badge>
                                  {fragment.extraction_theme && (
                                    <Badge variant="secondary" className="text-xs">
                                      {fragment.extraction_theme}
                                    </Badge>
                                  )}
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* 已保存片段列表 */}
          {document.fragments && document.fragments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">
                  已保存片段 ({document.fragments.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {document.fragments.map((fragment) => (
                  <Card key={fragment.id} className="bg-muted/50">
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium">{fragment.title}</h4>
                          <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">{fragment.content}</p>
                          {fragment.summary && (
                            <p className="text-xs text-muted-foreground mt-1 italic">{fragment.summary}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2">
                            <Badge variant="outline" className="text-xs">
                              {fragment.generation_method === 'auto' ? '自动生成' :
                               fragment.generation_method === 'user_extraction' ? '主题提取' : '手动创建'}
                            </Badge>
                            {fragment.is_modified && (
                              <Badge variant="secondary" className="text-xs">已修改</Badge>
                            )}
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteSavedFragment(fragment.id!)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* 侧边栏 */}
        <div className="space-y-6">
          {/* 文档信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">文档信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <Label className="text-muted-foreground">文档ID</Label>
                <p>{document.id}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">源类型</Label>
                <p>{sourceTypeBadge?.label || document.source_type}</p>
              </div>
              {document.source_path && (
                <div>
                  <Label className="text-muted-foreground">文件路径</Label>
                  <p className="font-mono text-xs break-all">{document.source_path}</p>
                </div>
              )}
              <div>
                <Label className="text-muted-foreground">处理状态</Label>
                <p>{statusBadge?.label || document.processing_status}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">片段数量</Label>
                <p>{document.fragment_count}</p>
              </div>
              {document.file_size && (
                <div>
                  <Label className="text-muted-foreground">文件大小</Label>
                  <p>{(document.file_size / 1024).toFixed(2)} KB</p>
                </div>
              )}
              <div>
                <Label className="text-muted-foreground">创建时间</Label>
                <p>{new Date(document.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">更新时间</Label>
                <p>{new Date(document.updated_at).toLocaleString('zh-CN')}</p>
              </div>
            </CardContent>
          </Card>

          {/* 使用提示 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">使用提示</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p>1. 使用LLM自动生成片段，适合从长文本中提取多个知识点</p>
                    <p>2. 使用主题提取，适合针对特定主题精确提取知识</p>
                    <p>3. 生成的片段可以编辑后再保存到数据库</p>
                    <p>4. 建议先生成片段预览，选择有用的保存</p>
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
