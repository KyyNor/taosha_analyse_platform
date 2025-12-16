"use client";

import { useEffect, useState, useRef } from "react";
import { toast } from 'sonner';
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Upload, Trash2 } from "lucide-react";
import {
  systemConfigService,
  type SystemConfig,
  type SystemConfigCreate,
  type ExcelParseResponse
} from "@/lib/services/fraudhunter/systemConfigService";

// Badge配置
const categoryBadgeConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  sql_variable: { label: "SQL变量", variant: "default" },
  system_param: { label: "系统参数", variant: "secondary" }
};

const typeBadgeConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  string: { label: "简单值", variant: "outline" },
  list: { label: "列表", variant: "default" },
  json_list: { label: "JSON列表", variant: "secondary" }
};

// 值预览组件
function ValuePreview({ config }: { config: SystemConfig }) {
  const value = config.config_value?.value;
  if (value === undefined || value === null) return <span className="text-muted-foreground">-</span>;

  if (config.config_type === 'string') {
    const str = String(value);
    return <span className="font-mono text-xs">{str.length > 30 ? str.slice(0, 30) + '...' : str}</span>;
  }

  if (config.config_type === 'list') {
    if (!Array.isArray(value)) return <span className="text-muted-foreground">-</span>;
    return <span className="text-xs">[{value.length} 项]</span>;
  }

  if (config.config_type === 'json_list') {
    if (!Array.isArray(value)) return <span className="text-muted-foreground">-</span>;
    return <span className="text-xs">[{value.length} 条记录]</span>;
  }

  return <span className="text-muted-foreground">-</span>;
}

export default function SystemConfigPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SystemConfig[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 编辑弹窗状态
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [saving, setSaving] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState<SystemConfigCreate>({
    config_category: 'sql_variable',
    config_key: '',
    config_desc: '',
    config_type: 'string',
    config_value: { value: '' },
    sql_in_convert: false,
    sort_order: 0
  });

  // Excel导入状态
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_excelData, setExcelData] = useState<ExcelParseResponse | null>(null);
  const [excelLoading, setExcelLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 列表值编辑状态（用于list类型）
  const [listValues, setListValues] = useState<string[]>([]);

  // JSON列表编辑状态（用于json_list类型）
  const [jsonListData, setJsonListData] = useState<Record<string, any>[]>([]);
  const [jsonListColumns, setJsonListColumns] = useState<string[]>([]);

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (categoryFilter !== 'all') params.category = categoryFilter;

      const response = await systemConfigService.list(params);
      setData(response.items || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error("Failed to load configs:", error);
      toast.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [searchQuery, categoryFilter, currentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, categoryFilter]);

  // 打开新建弹窗
  const handleAdd = () => {
    setEditingConfig(null);
    setFormData({
      config_category: 'sql_variable',
      config_key: '',
      config_desc: '',
      config_type: 'string',
      config_value: { value: '' },
      sql_in_convert: false,
      sort_order: 0
    });
    setListValues([]);
    setJsonListData([]);
    setJsonListColumns([]);
    setExcelData(null);
    setDialogOpen(true);
  };

  // 打开编辑弹窗
  const handleEdit = (item: SystemConfig) => {
    setEditingConfig(item);
    setFormData({
      config_category: item.config_category,
      config_key: item.config_key,
      config_desc: item.config_desc,
      config_type: item.config_type,
      config_value: item.config_value,
      sql_in_convert: item.sql_in_convert,
      sort_order: item.sort_order
    });

    // 初始化列表值
    if (item.config_type === 'list' && Array.isArray(item.config_value?.value)) {
      setListValues(item.config_value.value.map(String));
    } else {
      setListValues([]);
    }

    // 初始化JSON列表
    if (item.config_type === 'json_list' && Array.isArray(item.config_value?.value)) {
      setJsonListData(item.config_value.value);
      if (item.config_value.value.length > 0) {
        setJsonListColumns(Object.keys(item.config_value.value[0]));
      }
    } else {
      setJsonListData([]);
      setJsonListColumns([]);
    }

    setExcelData(null);
    setDialogOpen(true);
  };

  // 保存配置
  const handleSave = async () => {
    // 表单验证
    if (!formData.config_key.trim()) {
      toast.error("请输入配置键");
      return;
    }
    if (!formData.config_desc.trim()) {
      toast.error("请输入配置描述");
      return;
    }

    // 根据类型组装config_value
    let configValue: any;
    if (formData.config_type === 'string') {
      configValue = { value: formData.config_value.value };
    } else if (formData.config_type === 'list') {
      configValue = { value: listValues.filter(v => v.trim()) };
    } else if (formData.config_type === 'json_list') {
      configValue = { value: jsonListData };
    }

    const saveData: SystemConfigCreate = {
      ...formData,
      config_value: configValue
    };

    setSaving(true);
    try {
      if (editingConfig) {
        await systemConfigService.update(editingConfig.id, saveData);
        toast.success("更新成功");
      } else {
        await systemConfigService.create(saveData);
        toast.success("创建成功");
      }
      setDialogOpen(false);
      loadData();
    } catch (error: any) {
      console.error("Failed to save config:", error);
      toast.error(error.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  // 处理Excel文件上传
  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setExcelLoading(true);
    try {
      const result = await systemConfigService.parseExcel(file);
      setExcelData(result);

      // 根据当前类型处理数据
      if (formData.config_type === 'list' && result.columns.length > 0) {
        // 取第一列作为列表值
        const values = result.data.map(row => String(row[result.columns[0]] || ''));
        setListValues(values);
        toast.success(`已导入 ${values.length} 项`);
      } else if (formData.config_type === 'json_list') {
        setJsonListColumns(result.columns);
        setJsonListData(result.data);
        toast.success(`已导入 ${result.row_count} 条记录`);
      }
    } catch (error: any) {
      console.error("Failed to parse Excel:", error);
      toast.error(error.response?.data?.detail || "解析Excel失败");
    } finally {
      setExcelLoading(false);
      // 重置文件输入
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 添加列表项
  const handleAddListItem = () => {
    setListValues([...listValues, '']);
  };

  // 删除列表项
  const handleRemoveListItem = (index: number) => {
    const newValues = [...listValues];
    newValues.splice(index, 1);
    setListValues(newValues);
  };

  // 更新列表项
  const handleListItemChange = (index: number, value: string) => {
    const newValues = [...listValues];
    newValues[index] = value;
    setListValues(newValues);
  };

  // 表格列配置
  const columns = [
    { key: "id", label: "ID", type: "number" as const },
    {
      key: "config_category",
      label: "分类",
      type: "badge" as const,
      badgeConfig: categoryBadgeConfig
    },
    { key: "config_key", label: "配置键", type: "text" as const },
    { key: "config_desc", label: "描述", type: "text" as const },
    {
      key: "config_type",
      label: "类型",
      type: "badge" as const,
      badgeConfig: typeBadgeConfig
    },
    {
      key: "config_value",
      label: "值预览",
      type: "custom" as const,
      render: (item: SystemConfig) => <ValuePreview config={item} />
    },
    { key: "sort_order", label: "排序", type: "number" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const }
  ];

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">系统配置</h1>
          <p className="text-muted-foreground">管理SQL变量和系统参数的热配置</p>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="flex gap-4 mb-4">
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="分类筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            <SelectItem value="sql_variable">SQL变量</SelectItem>
            <SelectItem value="system_param">系统参数</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={loadData}
        onAdd={handleAdd}
        onEdit={handleEdit}
        searchPlaceholder="搜索配置键或描述..."
        emptyText="暂无配置数据"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        pagination={{
          pageSize,
          currentPage,
          total,
          onPageChange: setCurrentPage,
        }}
      />

      {/* 新建/编辑弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingConfig ? '编辑配置' : '新建配置'}</DialogTitle>
            <DialogDescription>
              {editingConfig ? '修改系统配置信息' : '创建新的系统配置'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* 基础信息 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>分类 *</Label>
                <Select
                  value={formData.config_category}
                  onValueChange={(v) => setFormData({ ...formData, config_category: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sql_variable">SQL变量</SelectItem>
                    <SelectItem value="system_param">系统参数</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>排序</Label>
                <Input
                  type="number"
                  value={formData.sort_order}
                  onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>配置键 *</Label>
              <Input
                value={formData.config_key}
                onChange={(e) => setFormData({ ...formData, config_key: e.target.value })}
                placeholder="例如：branch_codes"
                disabled={!!editingConfig}
              />
              {!editingConfig && (
                <p className="text-xs text-muted-foreground">SQL中使用 {'${配置键}'} 引用</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>配置描述 *</Label>
              <Input
                value={formData.config_desc}
                onChange={(e) => setFormData({ ...formData, config_desc: e.target.value })}
                placeholder="简要描述配置的用途"
              />
            </div>

            {/* 值类型选择 */}
            <div className="space-y-2">
              <Label>值类型 *</Label>
              <Select
                value={formData.config_type}
                onValueChange={(v) => {
                  setFormData({ ...formData, config_type: v, config_value: { value: '' } });
                  setListValues([]);
                  setJsonListData([]);
                  setJsonListColumns([]);
                  setExcelData(null);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="string">简单值</SelectItem>
                  <SelectItem value="list">列表</SelectItem>
                  <SelectItem value="json_list">JSON列表</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* SQL转换选项（仅对list类型显示） */}
            {formData.config_type === 'list' && (
              <div className="flex items-center space-x-2">
                <Switch
                  checked={formData.sql_in_convert}
                  onCheckedChange={(checked) => setFormData({ ...formData, sql_in_convert: checked })}
                />
                <Label>转换为SQL IN格式</Label>
                <span className="text-xs text-muted-foreground">
                  (开启后值会转换为 &apos;a&apos;,&apos;b&apos;,&apos;c&apos; 格式)
                </span>
              </div>
            )}

            {/* 值编辑器 - 简单值 */}
            {formData.config_type === 'string' && (
              <div className="space-y-2">
                <Label>配置值</Label>
                <Input
                  value={formData.config_value.value || ''}
                  onChange={(e) => setFormData({ ...formData, config_value: { value: e.target.value } })}
                  placeholder="输入配置值"
                />
              </div>
            )}

            {/* 值编辑器 - 列表 */}
            {formData.config_type === 'list' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>配置值列表</Label>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".xlsx,.xls"
                      onChange={handleExcelUpload}
                      className="hidden"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={excelLoading}
                    >
                      <Upload className="h-4 w-4 mr-1" />
                      {excelLoading ? '导入中...' : '导入Excel'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleAddListItem}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      添加
                    </Button>
                  </div>
                </div>
                <div className="space-y-2 max-h-60 overflow-y-auto border rounded-md p-2">
                  {listValues.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      暂无数据，点击"添加"或"导入Excel"
                    </p>
                  ) : (
                    listValues.map((value, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Input
                          value={value}
                          onChange={(e) => handleListItemChange(index, e.target.value)}
                          placeholder={`值 ${index + 1}`}
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveListItem(index)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
                <p className="text-xs text-muted-foreground">共 {listValues.filter(v => v.trim()).length} 项</p>
              </div>
            )}

            {/* 值编辑器 - JSON列表 */}
            {formData.config_type === 'json_list' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>JSON列表数据</Label>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".xlsx,.xls"
                      onChange={handleExcelUpload}
                      className="hidden"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={excelLoading}
                    >
                      <Upload className="h-4 w-4 mr-1" />
                      {excelLoading ? '导入中...' : '导入Excel'}
                    </Button>
                  </div>
                </div>
                {jsonListData.length === 0 ? (
                  <div className="border rounded-md p-4 text-center text-muted-foreground">
                    暂无数据，请导入Excel文件
                  </div>
                ) : (
                  <div className="border rounded-md max-h-60 overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {jsonListColumns.map((col) => (
                            <TableHead key={col}>{col}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {jsonListData.slice(0, 10).map((row, index) => (
                          <TableRow key={index}>
                            {jsonListColumns.map((col) => (
                              <TableCell key={col} className="text-xs">
                                {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    {jsonListData.length > 10 && (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        仅显示前10条，共 {jsonListData.length} 条记录
                      </p>
                    )}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">共 {jsonListData.length} 条记录</p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
