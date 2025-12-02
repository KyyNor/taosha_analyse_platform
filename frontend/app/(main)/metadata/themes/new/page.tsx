"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createTheme, getTables, addTableToTheme } from "@/lib/services/metadataService";
import { ArrowLeft, Save, X, Plus, FolderOpen, Database } from "lucide-react";
import { toast } from "sonner";

interface NewDataTheme {
  theme_name: string;
  theme_description: string;
  theme_type: string;
  department: string;
}

const THEME_TYPES = [
  { value: "normal", label: "一般主题" },
  { value: "public", label: "通用主题" },
];

export default function NewDataThemePage() {
  const router = useRouter();

  const [themeData, setThemeData] = useState<NewDataTheme>({
    theme_name: '',
    theme_description: '',
    theme_type: '',
    department: '',
  });

  const [saving, setSaving] = useState(false);
  const [allTables, setAllTables] = useState<any[]>([]);
  const [selectedTables, setSelectedTables] = useState<any[]>([]);
  const [addingTable, setAddingTable] = useState(false);
  const [tableSearch, setTableSearch] = useState("");
  const [createdThemeId, setCreatedThemeId] = useState<number | null>(null);

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
    loadAllTables();
  }, []);

  // 主题数据更新处理
  const handleThemeDataChange = (field: keyof NewDataTheme, value: any) => {
    setThemeData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证基本信息
    if (!themeData.theme_name || themeData.theme_name.trim() === '') {
      errors.push('主题名称不能为空');
    }

    if (!themeData.theme_type) {
      errors.push('主题类型不能为空');
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
      const createResult = await createTheme({
        theme_name: themeData.theme_name,
        theme_description: themeData.theme_description,
        theme_type: themeData.theme_type,
        department: themeData.department,
      });

      setCreatedThemeId(createResult.data.id);
      toast.success('数据主题创建成功');
    } catch (error) {
      console.error('Failed to create theme:', error);
      toast.error('创建失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 添加表到新建的主题
  const handleAddTableToNewTheme = async (tableId: number) => {
    if (!createdThemeId) return;

    try {
      await addTableToTheme(createdThemeId, tableId);
      // 添加到已选表列表
      const table = allTables.find(t => t.id === tableId);
      if (table) {
        setSelectedTables(prev => [...prev, table]);
      }
      toast.success('表已添加到主题');
    } catch (error) {
      console.error('Failed to add table to theme:', error);
      toast.error('添加表失败');
    }
  };

  // 完成创建并跳转
  const handleFinish = () => {
    if (createdThemeId) {
      router.push(`/metadata/themes/${createdThemeId}`);
    } else {
      router.push('/metadata/themes');
    }
  };

  const handleCancel = () => {
    if (confirm('确定要取消创建数据主题吗？')) {
      router.push('/metadata/themes');
    }
  };

  const handleBack = () => {
    if (createdThemeId) {
      router.push(`/metadata/themes/${createdThemeId}`);
    } else {
      router.push('/metadata/themes');
    }
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
              {createdThemeId ? <Database className="h-6 w-6" /> : <FolderOpen className="h-6 w-6" />}
              {createdThemeId ? '关联数据表' : '新建数据主题'}
            </h1>
            <p className="text-muted-foreground">
              {createdThemeId ? '为新建的主题选择相关的数据表' : '创建新的数据主题并组织相关的数据表'}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {!createdThemeId ? (
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
                {saving ? '创建中...' : '创建主题'}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => setAddingTable(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                添加表
              </Button>
              <Button onClick={handleFinish}>
                完成创建
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主要内容 */}
        <div className="lg:col-span-2 space-y-6">
          {!createdThemeId ? (
            <>
              {/* 基本信息 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">基本信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="theme-name">主题名称 *</Label>
                      <Input
                        id="theme-name"
                        value={themeData.theme_name}
                        onChange={(e) => handleThemeDataChange('theme_name', e.target.value)}
                        placeholder="请输入主题名称"
                      />
                      <p className="mt-1 text-sm text-gray-500">主题名称应简洁明了，便于用户理解</p>
                    </div>
                    <div>
                      <Label htmlFor="theme-type">主题类型 *</Label>
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
                      <p className="mt-1 text-sm text-gray-500">根据主题的主要用途选择合适类型</p>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="department">关联部门</Label>
                    <Input
                      id="department"
                      value={themeData.department}
                      onChange={(e) => handleThemeDataChange('department', e.target.value)}
                      placeholder="请输入关联部门"
                    />
                    <p className="mt-1 text-sm text-gray-500">输入主要负责此主题的业务部门</p>
                  </div>
                  <div>
                    <Label htmlFor="theme-description">主题描述</Label>
                    <Textarea
                      id="theme-description"
                      value={themeData.theme_description}
                      onChange={(e) => handleThemeDataChange('theme_description', e.target.value)}
                      placeholder="请输入主题的详细描述、使用场景和价值说明"
                      rows={4}
                    />
                    <p className="mt-1 text-sm text-gray-500">详细描述主题的业务价值、应用场景和包含的数据范围</p>
                  </div>
                </CardContent>
              </Card>

              {/* 创建后说明 */}
              <Card className="border-l-4 border-l-green-500">
                <CardContent className="pt-6">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                        <span className="text-green-600 text-sm font-medium">✓</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-green-800">创建后操作</h3>
                      <p className="mt-1 text-sm text-green-700">
                        主题创建成功后，您可以在详情页面关联相关的数据表，帮助用户更好地组织和发现数据资源。
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <>
              {/* 已选择的表 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">已选择的表</CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedTables.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded">
                      暂未选择任何表
                      <p className="text-sm mt-2">点击上方"添加表"按钮开始选择数据表</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {selectedTables.map((table) => (
                        <div key={table.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex-1">
                            <h4 className="font-medium">{table.name}</h4>
                            {table.comment && (
                              <p className="text-sm text-gray-500 mt-1">{table.comment}</p>
                            )}
                          </div>
                          <div className="text-green-600">
                            <Plus className="h-4 w-4" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>

        {/* 侧边栏信息 */}
        <div className="space-y-6">
          {/* 主题类型说明 */}
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
                    <p><strong>一般主题：</strong>面向特定业务领域的数据组织</p>
                    <p><strong>通用主题：</strong>面向多个业务领域的共享数据集合</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 命名建议 */}
          <Card className="border-l-4 border-l-yellow-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                    <span className="text-yellow-600 text-sm font-medium">!</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-yellow-800">命名建议</h3>
                  <div className="mt-2 text-sm text-yellow-700 space-y-1">
                    <p>• 使用简洁明了的中文名称</p>
                    <p>• 避免使用技术术语和缩写</p>
                    <p>• 体现主题的核心业务价值</p>
                    <p>• 保持与同类主题的命名一致性</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 最佳实践 */}
          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center">
                    <span className="text-purple-600 text-sm font-medium">★</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-purple-800">最佳实践</h3>
                  <div className="mt-2 text-sm text-purple-700 space-y-1">
                    <p>• 一个主题专注于一个业务领域</p>
                    <p>• 关联的表应具有明确的业务关系</p>
                    <p>• 定期维护和更新主题内容</p>
                    <p>• 提供清晰的描述和使用指南</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 表选择对话框 */}
      {addingTable && createdThemeId && (
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
              {allTables.filter(table =>
                !selectedTables.some(selected => selected.id === table.id) &&
                (tableSearch === "" || table.name.toLowerCase().includes(tableSearch.toLowerCase()))
              ).length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {tableSearch ? "没有找到匹配的表" : "没有可关联的表"}
                </div>
              ) : (
                <div className="divide-y">
                  {allTables.filter(table =>
                    !selectedTables.some(selected => selected.id === table.id) &&
                    (tableSearch === "" || table.name.toLowerCase().includes(tableSearch.toLowerCase()))
                  ).map((table) => (
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
                          handleAddTableToNewTheme(table.id);
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
    </div>
  );
}