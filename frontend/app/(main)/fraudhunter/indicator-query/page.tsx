"use client";

import { useEffect, useState } from "react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Trash2, Plus, Search, ChevronDown, ChevronUp, Calendar, FileText, Clock } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Separator } from "@/components/ui/separator";
import { indicatorQueryService } from "@/lib/services/fraudhunterService";
import {
  WideTableFile,
  IndicatorInfo,
  IndicatorQueryCondition,
  IndicatorQueryResponse,
  WideTableFilesResponse
} from "@/types/fraudhunter/indicatorQuery";

// 对象类型选项
const OBJECT_TYPE_OPTIONS = [
  { value: "cust_no", label: "客户号" },
  { value: "dep_acct_no", label: "存款账户" },
  { value: "loan_acct_no", label: "贷款账户" },
];

// 运算符选项
const OPERATOR_OPTIONS = [
  { value: "=", label: "等于" },
  { value: ">", label: "大于" },
  { value: "<", label: "小于" },
  { value: ">=", label: "大于等于" },
  { value: "<=", label: "小于等于" },
  { value: "like", label: "包含" },
];

export default function DataQueryPage() {
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [wideTableFiles, setWideTableFiles] = useState<WideTableFile[]>([]);
  const [indicators, setIndicators] = useState<IndicatorInfo[]>([]);
  const [queryResult, setQueryResult] = useState<IndicatorQueryResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fileListPage, setFileListPage] = useState(1);
  const [fileListTotalPages, setFileListTotalPages] = useState(1);

  // 查询参数
  const [objectType, setObjectType] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<WideTableFile | null>(null);
  const [dateFilter, setDateFilter] = useState<string>("");
  const [conditions, setConditions] = useState<IndicatorQueryCondition[]>([
    {
      id: "target_id",
      field: "target_id",
      operator: "=",
      value: "",
      field_name: "对象ID"
    }
  ]);
  const [isQueryConditionsCollapsed, setIsQueryConditionsCollapsed] = useState(false);

  // 加载宽表文件列表
  const loadWideTableFiles = async (page: number = 1) => {
    if (!objectType) return;

    try {
      setLoading(true);
      const response: WideTableFilesResponse = await indicatorQueryService.getWideTableFiles({
        object_type: objectType,
        date_filter: dateFilter || undefined,
        page,
        page_size: 10
      });
      setWideTableFiles(response.items);
      setFileListTotalPages(response.total_pages);
      setFileListPage(response.page);
    } catch (error) {
      console.error("Failed to load wide table files:", error);
      toast.error("加载宽表文件列表失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载指标列表
  const loadIndicators = async (snapshotId: number) => {
    try {
      const response = await indicatorQueryService.getIndicatorsBySnapshot(snapshotId);
      setIndicators(response);
    } catch (error) {
      console.error("Failed to load indicators:", error);
      toast.error("加载指标列表失败");
    }
  };

  // 选择宽表文件
  const handleSelectFile = (file: WideTableFile) => {
    setSelectedFile(file);
    loadIndicators(file.id);
    // 重置查询条件（保留target_id）
    setConditions([
      {
        id: "target_id",
        field: "target_id",
        operator: "=",
        value: "",
        field_name: "对象ID"
      }
    ]);
    setQueryResult(null);
    setIsQueryConditionsCollapsed(false);
  };

  // 添加查询条件
  const addCondition = () => {
    if (conditions.length >= 10) {
      toast.error("最多只能添加10个查询条件");
      return;
    }
    if (indicators.length <= 1) { // 只有target_id
      toast.error("没有可用的指标字段");
      return;
    }
    setConditions([...conditions, {
      id: Date.now().toString(),
      field: "",
      operator: "=",
      value: ""
    }]);
  };

  // 删除查询条件
  const removeCondition = (id: string) => {
    if (id === "target_id") {
      toast.error("对象ID条件不能删除");
      return;
    }
    setConditions(conditions.filter(c => c.id !== id));
  };

  // 更新查询条件
  const updateCondition = (id: string, field: keyof IndicatorQueryCondition, value: any) => {
    setConditions(conditions.map(c =>
      c.id === id ? { ...c, [field]: value } : c
    ));
  };

  // 执行查询
  const executeQuery = async (page: number = 1) => {
    if (!selectedFile) {
      toast.error("请先选择宽表文件");
      return;
    }

    // 检查target_id是否有值
    const targetIdCondition = conditions.find(c => c.field === "target_id");
    if (!targetIdCondition || !targetIdCondition.value) {
      toast.error("请输入对象ID");
      return;
    }

    setQuerying(true);
    try {
      const queryParams = {
        snapshot_id: selectedFile.id,
        target_id: targetIdCondition.value,
        conditions: conditions
          .filter(c => c.field && c.value && c.field !== "target_id")
          .map(({ field, operator, value }) => ({
            field,
            operator,
            value
          })),
        page,
        page_size: 100
      };

      const response = await indicatorQueryService.queryData(queryParams);
      setQueryResult(response);
      setCurrentPage(response.page);
      setTotalPages(Math.ceil(response.total / response.page_size));

      // 查询后自动收起条件
      setIsQueryConditionsCollapsed(true);
    } catch (error) {
      console.error("Failed to query data:", error);
      toast.error("查询数据失败");
    } finally {
      setQuerying(false);
    }
  };

  // 获取运算符选项
  const getOperatorOptions = (dataType?: string) => {
    if (!dataType) return OPERATOR_OPTIONS.filter(op => op.value === "=" || op.value === "like");

    switch (dataType) {
      case "integer":
      case "float":
      case "date":
        return OPERATOR_OPTIONS.filter(op => op.value !== "like");
      case "string":
      default:
        return OPERATOR_OPTIONS.filter(op => op.value === "=" || op.value === "like");
    }
  };

  // 获取当前选中的指标
  const getSelectedIndicator = (field: string) => {
    return indicators.find(ind => ind.indicator_code === field);
  };

  // 格式化文件大小
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "-";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + " " + sizes[i];
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("zh-CN");
  };

  // 格式化时间
  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN");
  };

  useEffect(() => {
    if (objectType) {
      loadWideTableFiles();
      setSelectedFile(null);
      setIndicators([]);
      setConditions([{
        id: "target_id",
        field: "target_id",
        operator: "=",
        value: "",
        field_name: "对象ID"
      }]);
      setQueryResult(null);
    }
  }, [objectType]);

  useEffect(() => {
    if (dateFilter && objectType) {
      loadWideTableFiles(1);
    }
  }, [dateFilter]);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">指标数据查询</h1>
      </div>

      {/* 第一步：选择宽表类型 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm">1</span>
            选择宽表类型
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {OBJECT_TYPE_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant={objectType === option.value ? "default" : "outline"}
                onClick={() => setObjectType(option.value)}
                className="h-16"
              >
                {option.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 第二步：选择宽表文件 */}
      {objectType && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm">2</span>
                选择宽表文件
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <Input
                  type="date"
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  placeholder="筛选日期"
                  className="w-40"
                />
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">加载中...</div>
            ) : (
              <div className="space-y-2">
                {wideTableFiles.map((file) => (
                  <div
                    key={file.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors hover:bg-accent ${
                      selectedFile?.id === file.id ? "border-primary bg-accent" : ""
                    }`}
                    onClick={() => handleSelectFile(file)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">
                            {formatDate(file.etl_date)}
                            {file.is_realtime && (
                              <Badge variant="secondary" className="ml-2">实时</Badge>
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {file.row_count?.toLocaleString()} 行 × {file.column_count} 列
                            {file.file_size_bytes && ` · ${formatFileSize(file.file_size_bytes)}`}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="w-4 h-4" />
                        {formatDateTime(file.generation_time)}
                      </div>
                    </div>
                  </div>
                ))}

                {wideTableFiles.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    没有找到符合条件的宽表文件
                  </div>
                )}

                {/* 分页 */}
                {fileListTotalPages > 1 && (
                  <div className="flex justify-center mt-4">
                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => loadWideTableFiles(fileListPage - 1)}
                            className={fileListPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>

                        {Array.from({ length: Math.min(5, fileListTotalPages) }, (_, i) => {
                          const page = i + 1;
                          return (
                            <PaginationItem key={page}>
                              <PaginationLink
                                onClick={() => loadWideTableFiles(page)}
                                isActive={page === fileListPage}
                                className="cursor-pointer"
                              >
                                {page}
                              </PaginationLink>
                            </PaginationItem>
                          );
                        })}

                        {fileListTotalPages > 5 && (
                          <PaginationItem>
                            <span className="px-4 py-2">...</span>
                          </PaginationItem>
                        )}

                        <PaginationItem>
                          <PaginationNext
                            onClick={() => loadWideTableFiles(fileListPage + 1)}
                            className={fileListPage === fileListTotalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 第三步：配置查询条件 */}
      {selectedFile && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm">3</span>
                配置查询条件
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsQueryConditionsCollapsed(!isQueryConditionsCollapsed)}
              >
                {isQueryConditionsCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </Button>
            </CardTitle>
          </CardHeader>

          {/* 收起状态 */}
          {isQueryConditionsCollapsed && queryResult && (
            <CardContent>
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">当前查询条件：</div>
                {conditions.map((condition) => (
                  condition.value && (
                    <Badge key={condition.id} variant="outline" className="mr-2">
                      {condition.field_name || condition.field} {condition.operator} {condition.value}
                    </Badge>
                  )
                ))}
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setIsQueryConditionsCollapsed(false)}
                >
                  修改条件
                </Button>
              </div>
            </CardContent>
          )}

          {/* 展开状态 */}
          {!isQueryConditionsCollapsed && (
            <CardContent className="space-y-4">
              {conditions.map((condition, index) => (
                <div key={condition.id} className="flex gap-2 items-end">
                  <div className="flex-1">
                    <Label className="text-sm text-muted-foreground">
                      {condition.id === "target_id" ? "对象ID" : "查询条件"}
                    </Label>
                    {condition.id === "target_id" ? (
                      <Input
                        value={condition.value}
                        onChange={(e) => updateCondition(condition.id, 'value', e.target.value)}
                        placeholder="请输入对象ID"
                        className="mt-1"
                      />
                    ) : (
                      <Select
                        value={condition.field}
                        onValueChange={(value) => updateCondition(condition.id, 'field', value)}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="选择指标" />
                        </SelectTrigger>
                        <SelectContent>
                          {indicators
                            .filter(ind => ind.indicator_code !== "target_id")
                            .map((indicator) => (
                            <SelectItem key={indicator.indicator_code} value={indicator.indicator_code}>
                              <div className="flex items-center gap-2">
                                <span>{indicator.indicator_name}</span>
                                <Badge variant="outline" className="text-xs">
                                  {indicator.indicator_code}
                                </Badge>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

                  {condition.field !== "target_id" && condition.field && (
                    <div className="w-32">
                      <Label className="text-sm text-muted-foreground">运算符</Label>
                      <Select
                        value={condition.operator}
                        onValueChange={(value) => updateCondition(condition.id, 'operator', value)}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {getOperatorOptions(getSelectedIndicator(condition.field)?.data_type).map(op => (
                            <SelectItem key={op.value} value={op.value}>
                              {op.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {condition.field !== "target_id" && condition.field && (
                    <div className="flex-1">
                      <Label className="text-sm text-muted-foreground">值</Label>
                      <Input
                        value={condition.value}
                        onChange={(e) => updateCondition(condition.id, 'value', e.target.value)}
                        placeholder="输入值"
                        className="mt-1"
                      />
                    </div>
                  )}

                  {condition.id !== "target_id" && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeCondition(condition.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}

              <div className="flex items-center justify-between pt-4">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addCondition}
                  disabled={conditions.length >= 10}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  添加条件
                </Button>

                <Button
                  onClick={() => executeQuery(1)}
                  disabled={querying || !conditions.find(c => c.field === "target_id" && c.value)}
                  className="w-32"
                >
                  <Search className="w-4 h-4 mr-2" />
                  {querying ? "查询中..." : "查询"}
                </Button>
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* 查询结果 */}
      {queryResult && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>查询结果</CardTitle>
              <div className="text-sm text-muted-foreground">
                共 {queryResult.total} 条记录，当前显示第 {queryResult.page} 页
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {queryResult.items.length > 0 ? (
              <>
                {/* 数据表格 */}
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {Object.keys(queryResult.items[0]).map((key) => (
                          <TableHead key={key}>{key}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {queryResult.items.map((row, index) => (
                        <TableRow key={index}>
                          {Object.values(row).map((value: any, idx: number) => (
                            <TableCell key={idx}>
                              {value?.toString() || "-"}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* 分页 */}
                {totalPages > 1 && (
                  <div className="mt-4">
                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => executeQuery(currentPage - 1)}
                            className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>

                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          const page = i + 1;
                          return (
                            <PaginationItem key={page}>
                              <PaginationLink
                                onClick={() => executeQuery(page)}
                                isActive={page === currentPage}
                                className="cursor-pointer"
                              >
                                {page}
                              </PaginationLink>
                            </PaginationItem>
                          );
                        })}

                        {totalPages > 5 && (
                          <PaginationItem>
                            <span className="px-4 py-2">...</span>
                          </PaginationItem>
                        )}

                        <PaginationItem>
                          <PaginationNext
                            onClick={() => executeQuery(currentPage + 1)}
                            className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                没有找到符合条件的数据
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}