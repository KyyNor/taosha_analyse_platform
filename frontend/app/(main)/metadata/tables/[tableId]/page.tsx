"use client";
import { useEffect, useState, memo, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { getTableById, getColumnsByTable, batchUpdateTableAndColumns, getRelations } from "@/lib/services/metadataService";
import { ArrowLeft, Edit, Database, Save, X, Trash2 } from "lucide-react";
import { formatDateTime, formatBoolean } from "@/lib/utils/formatUtils";
import { toast } from "sonner";
import { useConfirmDialog } from "@/components/ui/confirm-dialog";

// 优化的字段行组件 - 使用memo避免不必要的重渲染
interface ColumnRowProps {
  column: any;
  index: number;
  relationConfigs: any[];
  onColumnChange: (index: number, field: string, value: any) => void;
  onDelete: (index: number) => void;
}

const ColumnRow = memo(({ column, index, relationConfigs, onColumnChange, onDelete }: ColumnRowProps) => {
  return (
    <TableRow>
      <TableCell>
        <Input
          value={column.name || ''}
          onChange={(e) => onColumnChange(index, 'name', e.target.value)}
          placeholder="字段名"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Input
          value={column.type || ''}
          onChange={(e) => onColumnChange(index, 'type', e.target.value)}
          placeholder="字段类型"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Input
          value={column.business_type || ''}
          onChange={(e) => onColumnChange(index, 'business_type', e.target.value)}
          placeholder="业务类型"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Input
          value={column.comment || ''}
          onChange={(e) => onColumnChange(index, 'comment', e.target.value)}
          placeholder="字段描述"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Input
          value={column.remark || ''}
          onChange={(e) => onColumnChange(index, 'remark', e.target.value)}
          placeholder="备注"
          className="h-8"
        />
      </TableCell>
      <TableCell>
        <Select
          value={column.relation_config_id?.toString() || '__none__'}
          onValueChange={(value) => onColumnChange(index, 'relation_config_id', value === '__none__' ? null : Number(value))}
        >
          <SelectTrigger className="h-8">
            <SelectValue placeholder="选择关系配置" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">无</SelectItem>
            {relationConfigs.map((config) => (
              <SelectItem key={config.id} value={config.id.toString()}>
                {config.relation_family}{config.relation_subfamily ? `|${config.relation_subfamily}` : ''}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Switch
          checked={column.is_available === 0}
          onCheckedChange={(checked) => onColumnChange(index, 'is_available', checked ? 0 : 1)}
        />
      </TableCell>
      <TableCell>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={() => onDelete(index)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </TableCell>
    </TableRow>
  );
});

ColumnRow.displayName = 'ColumnRow';

export default function TableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const tableId = params?.tableId as string;
  const mode = searchParams?.get('mode');
  const { confirm, DialogComponent } = useConfirmDialog();

  const [loading, setLoading] = useState(true);
  const [tableData, setTableData] = useState<any>(null);
  const [originalTableData, setOriginalTableData] = useState<any>(null);
  const [columnsData, setColumnsData] = useState<any[]>([]);
  const [originalColumnsData, setOriginalColumnsData] = useState<any[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(mode === 'edit');
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [relationConfigs, setRelationConfigs] = useState<any[]>([]);

  // 加载表基本信息
  const loadTableData = async () => {
    try {
      const res = await getTableById(Number(tableId));
      setTableData(res);
      setOriginalTableData(JSON.parse(JSON.stringify(res))); // 深拷贝保存原始数据
    } catch (error) {
      console.error('Failed to load table data:', error);
      toast.error('加载表数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载字段信息
  const loadColumnsData = async () => {
    setColumnsLoading(true);
    try {
      const res = await getColumnsByTable(Number(tableId));
      const columns = Array.isArray(res?.data) ? res.data : res;
      setColumnsData(columns);
      setOriginalColumnsData(JSON.parse(JSON.stringify(columns))); // 深拷贝保存原始数据
    } catch (error) {
      console.error('Failed to load columns data:', error);
      toast.error('加载字段数据失败');
    } finally {
      setColumnsLoading(false);
    }
  };

  // 加载关系配置列表
  const loadRelationConfigs = async () => {
    try {
      const res = await getRelations({ page: 1, page_size: 1000 });
      const configs = Array.isArray(res?.items) ? res.items : [];
      setRelationConfigs(configs);
    } catch (error) {
      console.error('Failed to load relation configs:', error);
    }
  };

  useEffect(() => {
    if (tableId) {
      loadTableData();
      loadColumnsData();
      loadRelationConfigs();
    }
  }, [tableId]);

  // 监听URL参数变化来切换编辑模式
  useEffect(() => {
    setIsEditMode(mode === 'edit');
  }, [mode]);

  // 检查数据是否有变化
  useEffect(() => {
    if (!originalTableData || !originalColumnsData) return;

    const tableChanged = JSON.stringify(tableData) !== JSON.stringify(originalTableData);
    const columnsChanged = JSON.stringify(columnsData) !== JSON.stringify(originalColumnsData);

    setHasChanges(tableChanged || columnsChanged);
  }, [tableData, columnsData, originalTableData, originalColumnsData]);

  const handleEdit = () => {
    router.push(`/metadata/tables/${tableId}?mode=edit`);
  };

  // 表单验证
  const validateForm = () => {
    const errors: string[] = [];

    // 验证表基本信息
    if (!tableData.name || tableData.name.trim() === '') {
      errors.push('表名不能为空');
    }

    // 验证字段信息
    if (columnsData.length === 0) {
      errors.push('至少需要一个字段');
    }

    columnsData.forEach((column, index) => {
      if (!column.name || column.name.trim() === '') {
        errors.push(`第 ${index + 1} 个字段的字段名不能为空`);
      }
      if (!column.type) {
        errors.push(`第 ${index + 1} 个字段的字段类型不能为空`);
      }
      // 检查字段名重复
      const duplicateNames = columnsData.filter((c, i) =>
        c.name && c.name.trim() !== '' && c.name === column.name && i !== index
      );
      if (duplicateNames.length > 0) {
        errors.push(`字段名 "${column.name}" 重复`);
      }
    });

    return errors;
  };

  const handleSave = async () => {
    if (!hasChanges) {
      toast.info('没有需要保存的更改');
      return;
    }

    // 表单验证
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('表单验证失败:\n' + errors.join('\n'));
      return;
    }

    setSaving(true);
    try {
      // 准备批量更新数据
      const updateData = {
        table: {
          id: Number(tableId),
          name: tableData.name,
          comment: tableData.comment,
          remark: tableData.remark,
          is_available: tableData.is_available,
        },
        columns: columnsData.map(column => ({
          id: column.id,
          table_id: Number(tableId),
          name: column.name,
          type: column.type,
          comment: column.comment,
          remark: column.remark,
          is_available: column.is_available,
          business_type: column.business_type,
          relation_config_id: column.relation_config_id,
        }))
      };

      // 批量更新表和字段信息
      await batchUpdateTableAndColumns(Number(tableId), updateData);

      // 更新成功后重新加载数据
      await Promise.all([
        loadTableData(),
        loadColumnsData()
      ]);

      // 退出编辑模式
      router.push(`/metadata/tables/${tableId}`);
      toast.success('保存成功');
    } catch (error) {
      console.error('Failed to save table data:', error);
      toast.error('保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (hasChanges) {
      confirm({
        title: '确认取消',
        description: '您有未保存的更改，确定要取消吗？',
        onConfirm: () => {
          // 恢复原始数据
          setTableData(JSON.parse(JSON.stringify(originalTableData)));
          setColumnsData(JSON.parse(JSON.stringify(originalColumnsData)));
          router.push(`/metadata/tables/${tableId}`);
        }
      });
    } else {
      router.push(`/metadata/tables/${tableId}`);
    }
  };

  const handleBack = () => {
    if (hasChanges && isEditMode) {
      confirm({
        title: '确认离开',
        description: '您有未保存的更改，确定要离开吗？',
        onConfirm: () => router.push('/metadata/tables')
      });
    } else {
      router.push('/metadata/tables');
    }
  };

  // 表数据更新处理
  const handleTableDataChange = (field: string, value: any) => {
    setTableData((prev: any) => ({
      ...prev,
      [field]: value
    }));
  };

  // 字段数据更新处理 - 使用useCallback优化性能
  const handleColumnDataChange = useCallback((index: number, field: string, value: any) => {
    setColumnsData((prev: any[]) => {
      const newColumns = [...prev];
      newColumns[index] = {
        ...newColumns[index],
        [field]: value
      };
      return newColumns;
    });
  }, []);

  // 添加新字段
  const handleAddColumn = () => {
    const newColumn = {
      id: `new_${Date.now()}`,
      table_id: Number(tableId),
      name: '',
      type: 'VARCHAR',
      comment: '',
      remark: '',
      is_available: true,
      business_type: '',
      relation_config_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setColumnsData(prev => [...prev, newColumn]);
  };

  // 删除字段 - 使用useCallback优化性能
  const handleDeleteColumn = useCallback((index: number) => {
    confirm({
      title: '确认删除',
      description: '确定要删除这个字段吗？',
      onConfirm: () => setColumnsData(prev => prev.filter((_, i) => i !== index)),
      variant: "destructive"
    });
  }, [confirm]);

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center gap-2 mb-6">
          <Button variant="outline" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
        </div>
        <div className="text-center py-8">加载中...</div>
      </div>
    );
  }

  if (!tableData) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center gap-2 mb-6">
          <Button variant="outline" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
        </div>
        <div className="text-center py-8">数据表不存在</div>
      </div>
    );
  }

  // 字段表格列配置
  const columnsColumns = [
    { key: "id", label: "字段ID", type: "number" as const },
    { key: "table_id", label: "表ID", type: "number" as const },
    { key: "name", label: "字段名", type: "text" as const },
    { key: "type", label: "字段类型", type: "text" as const },
    { key: "comment", label: "字段描述", type: "text" as const, maxLength: 50 },
    { key: "remark", label: "备注", type: "text" as const, maxLength: 50 },
    { key: "is_available", label: "是否可用", type: "boolean" as const },
    { key: "business_type", label: "业务类型", type: "text" as const },
    { key: "relation_config_id", label: "关系配置", type: "number" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

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
              <Database className="h-6 w-6" />
              {tableData.table_name || tableData.name}
            </h1>
            <p className="text-muted-foreground">
              {isEditMode ? '编辑数据表信息' : '数据表详细信息'}
              {hasChanges && <span className="text-orange-600 ml-2">(有未保存的更改)</span>}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {isEditMode ? (
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
                disabled={saving || !hasChanges}
              >
                <Save className="h-4 w-4 mr-2" />
                {saving ? '保存中...' : '保存'}
              </Button>
            </>
          ) : (
            <Button onClick={handleEdit}>
              <Edit className="h-4 w-4 mr-2" />
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* 表基本信息 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditMode ? (
              <>
                <div>
                  <Label htmlFor="table-id">表ID</Label>
                  <Input
                    id="table-id"
                    value={tableData.id}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <div>
                  <Label htmlFor="table-name">表名 *</Label>
                  <Input
                    id="table-name"
                    value={tableData.name || ''}
                    onChange={(e) => handleTableDataChange('name', e.target.value)}
                    placeholder="请输入表名"
                  />
                </div>
                <div>
                  <Label htmlFor="table-comment">表描述</Label>
                  <Textarea
                    id="table-comment"
                    value={tableData.comment || ''}
                    onChange={(e) => handleTableDataChange('comment', e.target.value)}
                    placeholder="请输入表描述"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="table-remark">备注</Label>
                  <Textarea
                    id="table-remark"
                    value={tableData.remark || ''}
                    onChange={(e) => handleTableDataChange('remark', e.target.value)}
                    placeholder="请输入备注"
                    rows={2}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="table-available"
                    checked={tableData.is_available === 0}
                    onCheckedChange={(checked) => handleTableDataChange('is_available', checked ? 0 : 1)}
                  />
                  <Label htmlFor="table-available">可用状态</Label>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">表ID</label>
                  <p className="text-lg font-semibold">{tableData.id}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">表名</label>
                  <p className="text-lg">{tableData.name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">表描述</label>
                  <p className="text-sm">{tableData.comment || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">备注</label>
                  <p className="text-sm">{tableData.remark || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">状态</label>
                  <div className="mt-1">
                    <Badge variant={tableData.is_available === 0 ? "default" : "secondary"}>
                      {tableData.is_available === 0 ? '可用' : '不可用'}
                    </Badge>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">统计信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">字段数量</label>
              <p className="text-lg font-semibold">{columnsData.length}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">创建时间</label>
              <p className="text-sm">{formatDateTime(tableData.created_at)}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">更新时间</label>
              <p className="text-sm">{formatDateTime(tableData.updated_at)}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 字段信息 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">字段信息</CardTitle>
            {isEditMode && (
              <Button
                onClick={handleAddColumn}
                size="sm"
                variant="outline"
              >
                添加字段
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isEditMode ? (
            <div className="space-y-4">
              {columnsLoading ? (
                <div className="text-center py-4">加载中...</div>
              ) : columnsData.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无字段信息，点击上方按钮添加字段
                </div>
              ) : (
                <div className="border rounded-md overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[140px]">字段名 *</TableHead>
                        <TableHead className="w-[100px]">类型 *</TableHead>
                        <TableHead className="w-[100px]">业务类型</TableHead>
                        <TableHead className="w-[160px]">字段描述</TableHead>
                        <TableHead className="w-[120px]">备注</TableHead>
                        <TableHead className="w-[180px]">关系配置</TableHead>
                        <TableHead className="w-[60px]">可用</TableHead>
                        <TableHead className="w-[60px]">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {columnsData.map((column, index) => (
                        <ColumnRow
                          key={column.id || index}
                          column={column}
                          index={index}
                          relationConfigs={relationConfigs}
                          onColumnChange={handleColumnDataChange}
                          onDelete={handleDeleteColumn}
                        />
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          ) : (
            <MetadataTable
              data={columnsData}
              columns={columnsColumns}
              loading={columnsLoading}
              showActions={false}
              searchPlaceholder="搜索字段..."
              emptyText="暂无字段信息"
            />
          )}
        </CardContent>
      </Card>
      <DialogComponent />
    </div>
  );
}