"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getThemeById, updateTheme, getThemeTables, addTableToTheme, removeTableFromTheme, getTables } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Edit3, Eye, Plus, Trash2, Link } from "lucide-react";
import { toast } from "sonner";

interface DataTheme {
  id: number;
  theme_name: string;
  theme_description: string;
  theme_type: string;
  department: string;
  created_at: string;
  updated_at: string;
}

interface ThemeTable {
  id: number;
  name: string;
  comment: string;
}

const THEME_TYPES = [
  { value: "normal", label: "一般主题" },
  { value: "public", label: "通用主题" },
];


export default function DataThemeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const themeId = params.themeId as string;
  const mode = searchParams.get("mode") || "view";

  const [themeData, setThemeData] = useState<DataTheme | null>(null);
  const [themeTables, setThemeTables] = useState<ThemeTable[]>([]);
  const [allTables, setAllTables] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addingTable, setAddingTable] = useState(false);
  const [tableSearch, setTableSearch] = useState("");

  // 加载主题数据
  const loadTheme = async () => {
    setLoading(true);
    try {
      const res = await getThemeById(Number(themeId));
      if (res.success) {
        setThemeData(res.data);
      } else {
        toast.error("加载数据主题失败");
      }
    } catch (error) {
      console.error("Failed to load theme:", error);
      toast.error("加载数据主题失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载关联表数据
  const loadThemeTables = async () => {
    try {
      const res = await getThemeTables(Number(themeId));
      if (res.success) {
        setThemeTables(res.data);
      }
    } catch (error) {
      console.error("Failed to load theme tables:", error);
    }
  };

  // 加载所有可用的表
  const loadAllTables = async () => {
    try {
      const res = await getTables({ fields: false });
      if (res.success) {
        setAllTables(res.data);
      }
    } catch (error) {
      console.error("Failed to load all tables:", error);
    }
  };

  useEffect(() => {
    if (themeId) {
      loadTheme();
      loadThemeTables();
      loadAllTables();
    }
  }, [themeId]);

  // 数据更新处理
  const handleThemeDataChange = (field: keyof DataTheme, value: any) => {
    if (!themeData) return;

    setThemeData(prev => ({
      ...prev!,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    if (!themeData) return errors;

    // 验证基本信息
    if (!themeData.theme_name || themeData.theme_name.trim() === '') {
      errors.push('主题名称不能为空');
    }

    if (!themeData.theme_type) {
      errors.push('主题类型不能为空');
    }

    if (!themeData.department) {
      errors.push('关联部门不能为空');
    }

    return errors;
  };

  // 保存处理
  const handleSave = async () => {
    if (!themeData) return;

    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      await updateTheme(Number(themeId), {
        theme_name: themeData.theme_name,
        theme_description: themeData.theme_description,
        theme_type: themeData.theme_type,
        department: themeData.department,
      });

      toast.success('数据主题更新成功');
      if (mode === "edit") {
        router.push(`/metadata/themes/${themeId}`);
      } else {
        await loadTheme(); // 重新加载数据
      }
    } catch (error) {
      console.error('Failed to update theme:', error);
      toast.error('更新失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 切换编辑模式
  const handleEdit = () => {
    router.push(`/metadata/themes/${themeId}?mode=edit`);
  };

  // 取消编辑
  const handleCancel = () => {
    if (confirm('确定要取消编辑吗？未保存的更改将丢失。')) {
      if (mode === "edit") {
        router.push(`/metadata/themes/${themeId}`);
      } else {
        router.push('/metadata/themes');
      }
    }
  };

  // 返回列表
  const handleBack = () => {
    router.push('/metadata/themes');
  };

  // 添加表到主题
  const handleAddTable = async (tableId: number) => {
    try {
      await addTableToTheme(Number(themeId), tableId);
      toast.success('表已添加到主题');
      setAddingTable(false); // 关闭对话框
      setTableSearch(""); // 清空搜索
      loadThemeTables(); // 重新加载表列表
    } catch (error) {
      console.error('Failed to add table to theme:', error);
      toast.error('添加表失败');
    }
  };

  // 从主题移除表
  const handleRemoveTable = async (tableId: number) => {
    if (!confirm('确定要移除这个表吗？')) return;

    try {
      await removeTableFromTheme(Number(themeId), tableId);
      toast.success('表已从主题移除');
      loadThemeTables(); // 重新加载表列表
    } catch (error) {
      console.error('Failed to remove table from theme:', error);
      toast.error('移除表失败');
    }
  };

  // 过滤可选择的表（排除已经关联的表）
  const availableTables = allTables.filter(table =>
    !themeTables.some(themeTable => themeTable.id === table.id) &&
    (tableSearch === "" || table.name.toLowerCase().includes(tableSearch.toLowerCase()))
  );

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

  if (!themeData) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">数据主题不存在</h2>
          <p className="text-gray-600 mb-6">请检查主题ID是否正确</p>
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
              {isEditing ? "编辑数据主题" : "数据主题详情"}
            </h1>
            <p className="text-muted-foreground">
              管理数据主题信息和关联的数据表
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
                  <Label htmlFor="theme-name">主题名称 *</Label>
                  {isEditing ? (
                    <Input
                      id="theme-name"
                      value={themeData.theme_name}
                      onChange={(e) => handleThemeDataChange('theme_name', e.target.value)}
                      placeholder="请输入主题名称"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {themeData.theme_name}
                    </div>
                  )}
                </div>
                <div>
                  <Label htmlFor="theme-type">主题类型 *</Label>
                  {isEditing ? (
                    <Select
                      value={themeData.theme_type}
                      onValueChange={(value) => handleThemeDataChange('theme_type', value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="选择主题类型" />
                      </SelectTrigger>
                      <SelectContent>
                        {THEME_TYPES.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {THEME_TYPES.find(t => t.value === themeData.theme_type)?.label || themeData.theme_type}
                    </div>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="department">关联部门 *</Label>
                  {isEditing ? (
                    <Input
                      id="department"
                      value={themeData.department}
                      onChange={(e) => handleThemeDataChange('department', e.target.value)}
                      placeholder="请输入关联部门"
                    />
                  ) : (
                    <div className="mt-1 p-2 bg-gray-50 rounded border min-h-[40px] flex items-center">
                      {themeData.department || '未设置'}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <Label htmlFor="theme-description">主题描述</Label>
                {isEditing ? (
                  <Textarea
                    id="theme-description"
                    value={themeData.theme_description}
                    onChange={(e) => handleThemeDataChange('theme_description', e.target.value)}
                    placeholder="请输入主题的详细描述"
                    rows={4}
                  />
                ) : (
                  <div className="mt-1 p-3 bg-gray-50 rounded border min-h-[100px] whitespace-pre-wrap">
                    {themeData.theme_description || '暂无描述'}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 关联表管理 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                关联数据表
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setAddingTable(true)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  添加表
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {themeTables.length === 0 ? (
                <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded">
                  暂无关联的数据表
                  {!isEditing && (
                    <p className="text-sm mt-2">点击上方"添加表"按钮开始关联</p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {themeTables.map((table) => (
                    <div key={table.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex-1">
                        <h4 className="font-medium">{table.name}</h4>
                        {table.comment && (
                          <p className="text-sm text-gray-500 mt-1">{table.comment}</p>
                        )}
                      </div>
                      {!isEditing && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveTable(table.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          移除
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 表选择对话框 */}
              {addingTable && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">选择要关联的数据表</h3>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setAddingTable(false);
                          setTableSearch("");
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>

                    {/* 搜索框 */}
                    <div className="mb-4">
                      <Input
                        placeholder="搜索表名..."
                        value={tableSearch}
                        onChange={(e) => setTableSearch(e.target.value)}
                        className="w-full"
                      />
                    </div>

                    {/* 表列表 */}
                    <div className="flex-1 overflow-y-auto border rounded">
                      {availableTables.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          {tableSearch ? "没有找到匹配的表" : "没有可关联的表"}
                        </div>
                      ) : (
                        <div className="divide-y">
                          {availableTables.map((table) => (
                            <div
                              key={table.id}
                              className="p-3 hover:bg-gray-50 flex items-center justify-between"
                            >
                              <div>
                                <h4 className="font-medium">{table.name}</h4>
                                {table.comment && (
                                  <p className="text-sm text-gray-500">{table.comment}</p>
                                )}
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAddTable(table.id);
                                }}
                              >
                                <Plus className="h-4 w-4 mr-1" />
                                添加
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mt-4 flex justify-end">
                      <Button
                        variant="outline"
                        onClick={() => {
                          setAddingTable(false);
                          setTableSearch("");
                        }}
                      >
                        取消
                      </Button>
                    </div>
                  </div>
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
                <Label className="text-sm font-medium text-gray-700">主题ID</Label>
                <div className="mt-1 text-sm text-gray-900">{themeData.id}</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">关联表数量</Label>
                <div className="mt-1 text-sm text-gray-900">{themeTables.length} 个</div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">创建时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(themeData.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-700">更新时间</Label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(themeData.updated_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 主题说明 */}
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 text-sm font-medium">i</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800">主题类型说明</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    <p><strong>一般主题：</strong>针对特定业务领域的数据组织</p>
                    <p><strong>通用主题：</strong>跨业务领域的通用数据集合</p>
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
                    数据主题帮助组织和分类数据表，便于用户快速找到相关的数据资源。关联的表将在主题页面中统一展示和管理。
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