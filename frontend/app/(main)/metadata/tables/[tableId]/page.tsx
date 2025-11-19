"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getTableById, getColumnsByTable } from "@/lib/services/metadataService";
import { ArrowLeft, Edit, Database } from "lucide-react";
import { formatDateTime, formatBoolean } from "@/lib/utils/formatUtils";

export default function TableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tableId = params.tableId as string;

  const [loading, setLoading] = useState(true);
  const [tableData, setTableData] = useState<any>(null);
  const [columnsData, setColumnsData] = useState<any[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);

  // 加载表基本信息
  const loadTableData = async () => {
    try {
      const res = await getTableById(Number(tableId));
      setTableData(res);
    } catch (error) {
      console.error('Failed to load table data:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载字段信息
  const loadColumnsData = async () => {
    setColumnsLoading(true);
    try {
      const res = await getColumnsByTable(Number(tableId));
      setColumnsData(Array.isArray(res?.data) ? res.data : res);
    } catch (error) {
      console.error('Failed to load columns data:', error);
    } finally {
      setColumnsLoading(false);
    }
  };

  useEffect(() => {
    if (tableId) {
      loadTableData();
      loadColumnsData();
    }
  }, [tableId]);

  const handleEdit = () => {
    router.push(`/metadata/tables/${tableId}?mode=edit`);
  };

  const handleBack = () => {
    router.push('/metadata/tables');
  };

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
              <Database className="h-6 w-6" />
              {tableData.table_name}
            </h1>
            <p className="text-muted-foreground">数据表详细信息</p>
          </div>
        </div>
        <Button onClick={handleEdit}>
          <Edit className="h-4 w-4 mr-2" />
          编辑
        </Button>
      </div>

      {/* 表基本信息 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
                <Badge variant={tableData.is_available ? "default" : "secondary"}>
                  {tableData.is_available ? '可用' : '不可用'}
                </Badge>
              </div>
            </div>
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

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">技术信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">存储引擎</label>
              <p className="text-sm">{tableData.engine || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">字符集</label>
              <p className="text-sm">{tableData.charset || '-'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">排序规则</label>
              <p className="text-sm">{tableData.collation || '-'}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 字段信息 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">字段信息</CardTitle>
        </CardHeader>
        <CardContent>
          <MetadataTable
            data={columnsData}
            columns={columnsColumns}
            loading={columnsLoading}
            showActions={false}
            searchPlaceholder="搜索字段..."
            emptyText="暂无字段信息"
          />
        </CardContent>
      </Card>
    </div>
  );
}