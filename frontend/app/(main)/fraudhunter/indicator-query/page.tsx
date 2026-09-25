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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Trash2, Plus, Search, ChevronDown, ChevronUp, Calendar, FileText, Clock, Database, Check, ChevronsUpDown, AlertCircle, RefreshCw, Loader2 } from "lucide-react";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { indicatorQueryService } from "@/lib/services/fraudhunterService";
import {
  WideTableFile,
  IndicatorInfo,
  IndicatorQueryCondition,
  IndicatorQueryResponse,
  WideTableFilesResponse,
  WideTableType
} from "@/types/fraudhunter/indicatorQuery";

// 运算符选项
const OPERATOR_OPTIONS = [
  { value: "=", label: "等于" },
  { value: ">", label: "大于" },
  { value: "<", label: "小于" },
  { value: ">=", label: "大于等于" },
  { value: "<=", label: "小于等于" },
  { value: "like", label: "包含" },
];

// 数据类型选项
type DataType = 'offline' | 'realtime';

interface TableTypeOption {
  value: WideTableType;
  label: string;
  dataType: DataType;
}

const TABLE_TYPE_OPTIONS: TableTypeOption[] = [
  { value: 'dep_acct_offline', label: '存款宽表', dataType: 'offline' },
  { value: 'loan_acct_offline', label: '贷款宽表', dataType: 'offline' },
  { value: 'cust_offline', label: '客户宽表', dataType: 'offline' },
  { value: 'dep_acct_realtime', label: '存款宽表', dataType: 'realtime' }
];

// 版本信息接口
interface VersionInfo {
  version: string;
  label: string;
  status: 'current' | 'target' | 'archived';
  fileCount: number;
}

// 日期选项接口
interface DateOption {
  value: string;
  label: string;
  file: WideTableFile;
}

export default function IndicatorQueryPage() {
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [dateLoading, setDateLoading] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [wideTableFiles, setWideTableFiles] = useState<WideTableFile[]>([]);
  const [indicators, setIndicators] = useState<IndicatorInfo[]>([]);
  const [queryResult, setQueryResult] = useState<IndicatorQueryResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // 错误处理和重试状态
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastFailedAction, setLastFailedAction] = useState<(() => Promise<void>) | null>(null);

  // 新的选择状态
  const [dataType, setDataType] = useState<DataType>('offline'); // 默认选择离线
  const [tableType, setTableType] = useState<WideTableType>('dep_acct_offline'); // 默认选择存款宽表
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<WideTableFile | null>(null);
  
  // 防抖处理
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
  
  // 版本和日期数据
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [dateOptions, setDateOptions] = useState<DateOption[]>([]);
  const [dateSearchOpen, setDateSearchOpen] = useState(false);
  const [dateSearchValue, setDateSearchValue] = useState('');

  // 查询条件
  const [conditions, setConditions] = useState<IndicatorQueryCondition[]>([]);
  const [isQueryConditionsCollapsed, setIsQueryConditionsCollapsed] = useState(false);

  // 防抖处理函数
  const debounceAction = (action: () => void, delay: number = 300) => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    const timer = setTimeout(action, delay);
    setDebounceTimer(timer);
  };

  // 错误处理辅助函数
  const handleError = (error: unknown, message: string, retryAction?: () => Promise<void>) => {
    console.error(message, error);
    
    // 根据错误类型提供更友好的错误信息
    let friendlyMessage = message;
    const errorObj = error as { message?: string; status?: number };
    if (errorObj?.message?.includes('timeout') || errorObj?.message?.includes('TIMEOUT')) {
      friendlyMessage = "请求超时，请检查网络连接";
    } else if (errorObj?.message?.includes('Network Error') || errorObj?.message?.includes('fetch')) {
      friendlyMessage = "网络连接失败，请检查网络状态";
    } else if (errorObj?.status === 404) {
      friendlyMessage = "请求的资源不存在";
    } else if (errorObj?.status === 500) {
      friendlyMessage = "服务器内部错误，请稍后重试";
    } else if (errorObj?.status === 403) {
      friendlyMessage = "没有权限访问该资源";
    }
    
    setError(friendlyMessage);
    if (retryAction) {
      setLastFailedAction(() => retryAction);
    }
    toast.error(friendlyMessage);
  };

  // 重试函数
  const handleRetry = async () => {
    if (!lastFailedAction || isRetrying) return;
    
    setIsRetrying(true);
    setError(null);
    setRetryCount(prev => prev + 1);
    
    try {
      await lastFailedAction();
      setLastFailedAction(null);
      setRetryCount(0);
      toast.success("操作重试成功");
    } catch (error) {
      handleError(error, "重试失败", lastFailedAction);
    } finally {
      setIsRetrying(false);
    }
  };

  // 清除错误状态
  const clearError = () => {
    setError(null);
    setLastFailedAction(null);
    setRetryCount(0);
  };

  // 加载宽表文件列表
  const loadWideTableFiles = async () => {
    if (!tableType) return;

    const action = async () => {
      setLoading(true);
      setError(null);
      
      const response: WideTableFilesResponse = await indicatorQueryService.getWideTableFiles({
        wide_table_type: tableType,
        page: 1,
        page_size: 100 // 获取更多数据用于版本和日期选择
      });
      setWideTableFiles(response.items);
      
      // 处理版本信息（仅离线数据）
      if (dataType === 'offline') {
        const versionMap = new Map<string, VersionInfo>();
        response.items.forEach(file => {
          if (file.version_hash) {
            const existing = versionMap.get(file.version_hash);
            if (!existing) {
              versionMap.set(file.version_hash, {
                version: file.version_hash,
                label: `版本 ${file.version_hash.substring(0, 8)}${file.version_status ? ` (${file.version_status})` : ''}`,
                status: (file.version_status as 'current' | 'target' | 'archived') || 'archived',
                fileCount: 1
              });
            } else {
              existing.fileCount++;
            }
          }
        });
        const versionList = Array.from(versionMap.values()).sort((a, b) => {
          // 按状态排序：current > target > archived
          const statusOrder = { current: 0, target: 1, archived: 2 };
          return statusOrder[a.status] - statusOrder[b.status];
        });
        setVersions(versionList);
        
        // 自动选择最新版本（如果还没有选择）
        if (versionList.length > 0 && !selectedVersion) {
          const latestVersion = versionList[0].version;
          setSelectedVersion(latestVersion);
          // 触发后续的日期选项加载
          debounceAction(() => {
            loadDateOptionsForVersion(response.items, latestVersion);
          });
        }
      } else {
        setVersions([]);
        setSelectedVersion('');
        // 实时数据直接加载日期选项
        debounceAction(() => {
          loadDateOptionsForVersion(response.items, null);
        });
      }
      
      toast.success(`成功加载 ${response.items.length} 个数据文件`);
    };

    try {
      await action();
    } catch (error) {
      handleError(error, "加载宽表文件列表失败", action);
    } finally {
      setLoading(false);
    }
  };

  // 为特定版本加载日期选项
  const loadDateOptionsForVersion = (files: WideTableFile[], version: string | null) => {
    setDateLoading(true);
    
    const filteredFiles = version
      ? files.filter(file => file.version_hash === version)
      : files;
    
    // 按日期倒序排列，确保最新的在前面
    const sortedFiles = filteredFiles.sort((a, b) => {
      const dateA = new Date(a.etl_date).getTime();
      const dateB = new Date(b.etl_date).getTime();
      return dateB - dateA; // 倒序：最新的在前
    });
    
    const dateOpts: DateOption[] = sortedFiles.map(file => ({
      value: file.etl_date,
      label: file.display_label || `${file.etl_date} (${file.row_count?.toLocaleString() || 0} 行)`,
      file: file
    }));
    
    setDateOptions(dateOpts);
    setDateLoading(false);
    
    // 自动选择最新日期（如果还没有选择）
    if (dateOpts.length > 0 && !selectedDate) {
      const latestDate = dateOpts[0];
      setSelectedDate(latestDate.value);
      setSelectedFile(latestDate.file);
      // 自动加载指标列表
      debounceAction(() => {
        loadIndicators(latestDate.file.id);
      });
    } else if (dateOpts.length === 0) {
      // 如果没有可用的日期选项，清空相关状态
      setSelectedDate('');
      setSelectedFile(null);
      setIndicators([]);
      toast.warning("该版本暂无可用的数据文件");
    }
  };

  // 加载日期选项
  const loadDateOptions = async () => {
    if (!tableType) return;
    
    const filteredFiles = dataType === 'offline' && selectedVersion
      ? wideTableFiles.filter(file => file.version_hash === selectedVersion)
      : wideTableFiles;
    
    // 按日期倒序排列，确保最新的在前面
    const sortedFiles = filteredFiles.sort((a, b) => {
      const dateA = new Date(a.etl_date).getTime();
      const dateB = new Date(b.etl_date).getTime();
      return dateB - dateA; // 倒序：最新的在前
    });
    
    const dateOpts: DateOption[] = sortedFiles.map(file => ({
      value: file.etl_date,
      label: file.display_label || `${file.etl_date} (${file.row_count?.toLocaleString() || 0} 行)`,
      file: file
    }));
    
    setDateOptions(dateOpts);
    
    // 自动选择最新日期（如果还没有选择且有可用选项）
    if (dateOpts.length > 0 && !selectedDate) {
      const latestDate = dateOpts[0];
      setSelectedDate(latestDate.value);
      setSelectedFile(latestDate.file);
      // 自动加载指标列表
      debounceAction(() => {
        loadIndicators(latestDate.file.id);
      });
    } else if (dateOpts.length === 0 && selectedDate) {
      // 如果之前有选择但现在没有可用选项，清空状态
      setSelectedDate('');
      setSelectedFile(null);
      setIndicators([]);
    }
  };

  // 加载指标列表
  const loadIndicators = async (snapshotId: number) => {
    const action = async () => {
      setLoading(true);
      setError(null);
      
      const response = await indicatorQueryService.getIndicatorsBySnapshot(snapshotId);
      setIndicators(response);
      toast.success(`成功加载 ${response.length} 个指标字段`);
    };

    try {
      await action();
    } catch (error) {
      handleError(error, "加载指标列表失败", action);
      setIndicators([]);
    } finally {
      setLoading(false);
    }
  };

  // 处理数据类型选择
  const handleDataTypeChange = (newDataType: DataType) => {
    // 防抖处理避免重复请求
    debounceAction(() => {
      clearError(); // 清除之前的错误状态
      setDataType(newDataType);
      // 重置后续选择
      const newTableType = newDataType === 'offline' ? 'dep_acct_offline' : 'dep_acct_realtime';
      setTableType(newTableType);
      setSelectedVersion('');
      setSelectedDate('');
      setSelectedFile(null);
      setIndicators([]);
      setConditions([]);
      setQueryResult(null);
      setIsQueryConditionsCollapsed(false);
      setVersions([]);
      setDateOptions([]);
      
      toast.success(`已切换到${newDataType === 'offline' ? '离线' : '实时'}数据模式`);
    });
  };

  // 处理表类型选择
  const handleTableTypeChange = (newTableType: WideTableType) => {
    // 防抖处理避免重复请求
    debounceAction(() => {
      clearError(); // 清除之前的错误状态
      setTableType(newTableType);
      // 重置后续选择
      setSelectedVersion('');
      setSelectedDate('');
      setSelectedFile(null);
      setIndicators([]);
      setConditions([]);
      setQueryResult(null);
      setIsQueryConditionsCollapsed(false);
      setVersions([]);
      setDateOptions([]);
      
      const tableOption = TABLE_TYPE_OPTIONS.find(opt => opt.value === newTableType);
      toast.success(`已选择${tableOption?.label || newTableType}`);
    });
  };

  // 处理版本选择
  const handleVersionChange = (newVersion: string) => {
    // 防抖处理避免重复请求
    debounceAction(() => {
      clearError(); // 清除之前的错误状态
      setSelectedVersion(newVersion);
      // 重置后续选择
      setSelectedDate('');
      setSelectedFile(null);
      setIndicators([]);
      setConditions([]);
      setQueryResult(null);
      setIsQueryConditionsCollapsed(false);
      
      // 重新加载日期选项
      if (wideTableFiles.length > 0) {
        loadDateOptionsForVersion(wideTableFiles, newVersion);
      }
      
      const versionInfo = versions.find(v => v.version === newVersion);
      toast.success(`已选择${versionInfo?.label || `版本 ${newVersion.substring(0, 8)}`}`);
    });
  };

  // 处理日期选择
  const handleDateChange = (newDate: string) => {
    // 防抖处理避免重复请求
    debounceAction(() => {
      setSelectedDate(newDate);
      const dateOption = dateOptions.find(opt => opt.value === newDate);
      if (dateOption) {
        setSelectedFile(dateOption.file);
        // 显示选择成功的提示
        toast.success(`已选择数据文件：${dateOption.label}`);
        // 自动加载指标列表
        loadIndicators(dateOption.file.id);
        // 重置查询条件
        setConditions([]);
        setQueryResult(null);
        setIsQueryConditionsCollapsed(false);
      }
    });
  };

  // 清空日期搜索 - 保留函数以备将来使用
  // const clearDateSearch = () => {
  //   setDateSearchValue('');
  // };

  // 处理日期搜索框的键盘事件
  const handleDateSearchKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      setDateSearchValue('');
      setDateSearchOpen(false);
    } else if (event.key === 'Enter') {
      const filteredOptions = getFilteredDateOptions();
      if (filteredOptions.length === 1) {
        // 如果只有一个匹配项，直接选择
        handleDateChange(filteredOptions[0].value);
        setDateSearchOpen(false);
        setDateSearchValue('');
      }
    }
  };

  // 添加查询条件
  const addCondition = () => {
    if (conditions.length >= 10) {
      toast.error("最多只能添加10个查询条件");
      return;
    }
    if (indicators.length === 0) {
      toast.error("没有可用的指标字段，请先选择数据文件");
      return;
    }
    
    const newCondition: IndicatorQueryCondition = {
      id: Date.now().toString(),
      field: "",
      operator: "=",
      value: ""
    };
    
    setConditions([...conditions, newCondition]);
    toast.success("已添加新的查询条件");
  };

  // 删除查询条件
  const removeCondition = (id: string) => {
    const conditionToRemove = conditions.find(c => c.id === id);
    setConditions(conditions.filter(c => c.id !== id));
    
    if (conditionToRemove?.field) {
      const indicator = getSelectedIndicator(conditionToRemove.field);
      toast.success(`已删除条件：${indicator?.indicator_name || conditionToRemove.field}`);
    }
  };

  // 更新查询条件
  const updateCondition = (id: string, field: keyof IndicatorQueryCondition, value: string) => {
    setConditions(conditions.map(c =>
      c.id === id ? { ...c, [field]: value } : c
    ));
    
    // 提供字段选择的反馈
    if (field === 'field' && value) {
      const indicator = getSelectedIndicator(value);
      if (indicator) {
        toast.success(`已选择指标：${indicator.indicator_name}`);
      }
    }
  };

  // 执行查询
  const executeQuery = async (page: number = 1) => {
    if (!selectedFile) {
      toast.error("请先选择宽表文件");
      return;
    }

    // 检查是否至少有一个有效条件
    const validConditions = conditions.filter(c => c.field && c.value);
    if (validConditions.length === 0) {
      toast.error("请至少添加一个查询条件");
      return;
    }

    const action = async () => {
      setQuerying(true);
      setError(null);
      
      // 查找target_id条件
      const targetIdCondition = conditions.find(c => c.field === "target_id" && c.value);

      const queryParams = {
        snapshot_id: selectedFile.id,
        // target_id是可选的，只在有值时传递
        ...(targetIdCondition ? { target_id: targetIdCondition.value } : {}),
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
      
      toast.success(`查询完成，找到 ${response.total} 条记录`);
    };

    try {
      await action();
    } catch (error) {
      handleError(error, "查询数据失败", action);
    } finally {
      setQuerying(false);
    }
  };

  // 获取运算符选项
  const getOperatorOptions = (dataType?: string) => {
    if (!dataType) return OPERATOR_OPTIONS.filter(op => op.value === "=" || op.value === "like");

    switch (dataType) {
      case "numeric":
      case "date":
        // 数值和日期类型支持比较运算符，不支持like
        return OPERATOR_OPTIONS.filter(op => op.value !== "like");
      case "text":
      default:
        // 文本类型只支持等于和包含
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

  // 格式化时间
  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN");
  };

  // 获取组件禁用状态
  const getComponentDisabledState = () => {
    return {
      dataType: false, // 数据类型始终可选
      tableType: !dataType, // 需要先选择数据类型
      version: !dataType || !tableType || dataType === 'realtime', // 需要数据类型和表类型，且仅离线数据需要版本
      date: !dataType || !tableType || (dataType === 'offline' && !selectedVersion) // 需要前置选择完成
    };
  };

  // 获取可用的表类型选项
  const getAvailableTableTypes = () => {
    return TABLE_TYPE_OPTIONS.filter(option => option.dataType === dataType);
  };

  // 检查选择是否完整 - 保留函数以备将来使用
  // const isSelectionComplete = () => {
  //   if (!dataType || !tableType) return false;
  //   if (dataType === 'offline' && !selectedVersion) return false;
  //   if (!selectedDate || !selectedFile) return false;
  //   return true;
  // };

  // 获取过滤后的日期选项（用于搜索）
  const getFilteredDateOptions = () => {
    if (!dateSearchValue.trim()) return dateOptions;
    
    const searchTerm = dateSearchValue.toLowerCase().trim();
    return dateOptions.filter(option => {
      // 支持多种搜索方式：标签、日期值、文件信息
      const labelMatch = option.label.toLowerCase().includes(searchTerm);
      const dateMatch = option.value.includes(searchTerm);
      const fileInfoMatch = option.file.display_label?.toLowerCase().includes(searchTerm);
      const rowCountMatch = option.file.row_count?.toString().includes(searchTerm);
      
      return labelMatch || dateMatch || fileInfoMatch || rowCountMatch;
    });
  };

  // 检查是否有可用的日期选项
  const hasDateOptions = () => {
    return dateOptions.length > 0;
  };

  // 检查搜索是否有结果
  const hasSearchResults = () => {
    return getFilteredDateOptions().length > 0;
  };

  useEffect(() => {
    if (tableType) {
      loadWideTableFiles();
    }
  }, [tableType]);

  useEffect(() => {
    if (wideTableFiles.length > 0) {
      loadDateOptions();
    }
  }, [wideTableFiles, selectedVersion]);

  // 初始化默认选择
  useEffect(() => {
    // 页面加载时设置默认值，确保完整的默认选择链
    if (!tableType) {
      setTableType('dep_acct_offline');
    }
  }, []);

  // 清理防抖定时器
  useEffect(() => {
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [debounceTimer]);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">指标数据查询</h1>
      </div>

      {/* 错误提示和重试 */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <div className="flex items-center gap-2">
              {retryCount > 0 && (
                <span className="text-xs text-muted-foreground">
                  已重试 {retryCount} 次
                </span>
              )}
              {lastFailedAction && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetry}
                  disabled={isRetrying}
                  className="h-8"
                >
                  {isRetrying ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      重试中...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3 h-3 mr-1" />
                      重试
                    </>
                  )}
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={clearError}
                className="h-8"
              >
                ×
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* 横向选择工具栏 */}
      <Card>
        <CardHeader>
          <CardTitle>选择数据表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 数据类型选择 */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">数据类型</Label>
              <Select value={dataType} onValueChange={handleDataTypeChange}>
                <SelectTrigger>
                  <SelectValue />
                  {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="offline">离线</SelectItem>
                  <SelectItem value="realtime">实时</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* 表类型选择 */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">表类型</Label>
              <Select 
                value={tableType} 
                onValueChange={handleTableTypeChange}
                disabled={getComponentDisabledState().tableType || loading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择表类型" />
                  {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                </SelectTrigger>
                <SelectContent>
                  {getAvailableTableTypes().map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 版本选择（仅离线数据显示） */}
            {dataType === 'offline' && (
              <div className="space-y-2">
                <Label className="text-sm font-medium">版本</Label>
                <Select 
                  value={selectedVersion} 
                  onValueChange={handleVersionChange}
                  disabled={getComponentDisabledState().version || loading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={loading ? "加载中..." : "选择版本"} />
                    {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((version) => (
                      <SelectItem key={version.version} value={version.version}>
                        <div className="flex items-center gap-2">
                          <span>{version.label}</span>
                          <Badge 
                            variant={version.status === 'current' ? 'default' : 'outline'}
                            className="text-xs"
                          >
                            {version.status}
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* 日期选择（支持搜索的下拉选择器） */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">数据日期</Label>
              <Popover open={dateSearchOpen} onOpenChange={setDateSearchOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={dateSearchOpen}
                    className="w-full justify-between"
                    disabled={getComponentDisabledState().date || loading || dateLoading}
                  >
                    {selectedDate
                      ? dateOptions.find((option) => option.value === selectedDate)?.label
                      : loading || dateLoading ? "加载中..." : hasDateOptions() ? "选择日期" : "暂无数据"}
                    {(loading || dateLoading) ? (
                      <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    ) : (
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-full p-0">
                  <Command>
                    <CommandInput 
                      placeholder={`搜索日期、文件名或行数... (共${dateOptions.length}项)`}
                      value={dateSearchValue}
                      onValueChange={setDateSearchValue}
                      onKeyDown={handleDateSearchKeyDown}
                    />
                    {!hasDateOptions() ? (
                      <CommandEmpty>
                        <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
                          <Calendar className="h-8 w-8 opacity-50" />
                          <div className="text-sm">暂无可用数据</div>
                          <div className="text-xs">请检查前面的选择是否正确</div>
                        </div>
                      </CommandEmpty>
                    ) : !hasSearchResults() ? (
                      <CommandEmpty>
                        <div className="flex flex-col items-center gap-2 py-6 text-muted-foreground">
                          <Search className="h-8 w-8 opacity-50" />
                          <div className="text-sm">未找到匹配的日期</div>
                          <div className="text-xs">尝试其他搜索关键词</div>
                        </div>
                      </CommandEmpty>
                    ) : (
                      <CommandGroup className="max-h-64 overflow-y-auto">
                        {dateSearchValue && (
                          <div className="px-2 py-1 text-xs text-muted-foreground border-b">
                            找到 {getFilteredDateOptions().length} 个匹配项
                          </div>
                        )}
                        {getFilteredDateOptions().map((option) => (
                          <CommandItem
                            key={option.value}
                            value={option.value}
                            onSelect={(currentValue) => {
                              handleDateChange(currentValue);
                              setDateSearchOpen(false);
                              setDateSearchValue('');
                            }}
                            className="cursor-pointer"
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                selectedDate === option.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            <div className="flex flex-col flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium truncate">{option.label}</span>
                                {option.file.is_realtime && (
                                  <Badge variant="secondary" className="text-xs shrink-0">
                                    <Clock className="w-3 h-3 mr-1" />
                                    实时
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{option.value}</span>
                                {option.file.row_count && (
                                  <>
                                    <span>•</span>
                                    <span>{option.file.row_count.toLocaleString()} 行</span>
                                  </>
                                )}
                                {option.file.file_size_bytes && (
                                  <>
                                    <span>•</span>
                                    <span>{formatFileSize(option.file.file_size_bytes)}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    )}
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {/* 选择状态指示 */}
          {selectedFile && (
            <div className="mt-4 p-3 bg-accent rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <span className="font-medium">已选择：</span>
                <span>{selectedFile.display_label}</span>
                {selectedFile.is_realtime && (
                  <Badge variant="secondary" className="text-xs">
                    <Clock className="w-3 h-3 mr-1" />
                    实时
                  </Badge>
                )}
                {selectedFile.version_status && (
                  <Badge
                    variant={selectedFile.version_status === 'current' ? 'default' : 'outline'}
                    className="text-xs"
                  >
                    {selectedFile.version_status}
                  </Badge>
                )}
                {selectedFile.storage_backend === 'duckdb' && (
                  <Badge variant="outline" className="text-xs">
                    Parquet
                  </Badge>
                )}
                <span className="text-muted-foreground ml-auto">
                  {formatDateTime(selectedFile.generation_time)}
                </span>
              </div>
              {indicators.length > 0 && (
                <div className="mt-2 text-xs text-muted-foreground">
                  已加载 {indicators.length} 个指标字段，可以开始配置查询条件
                </div>
              )}
            </div>
          )}

          {/* 选择进度指示 */}
          {!selectedFile && (
            <div className="mt-4 p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Database className="w-4 h-4" />
                <span>
                  {!dataType ? "请选择数据类型" :
                   !tableType ? "请选择表类型" :
                   dataType === 'offline' && !selectedVersion ? "请选择版本" :
                   !selectedDate ? "请选择数据日期" :
                   loading ? "正在加载数据..." : "选择完成"}
                </span>
                {(loading || dateLoading) && (
                  <div className="ml-auto">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  </div>
                )}
              </div>
              {/* 进度条 */}
              <div className="mt-2 w-full bg-muted rounded-full h-1">
                <div 
                  className="bg-primary h-1 rounded-full transition-all duration-300"
                  style={{
                    width: `${
                      !dataType ? '0%' :
                      !tableType ? '25%' :
                      dataType === 'offline' && !selectedVersion ? '50%' :
                      !selectedDate ? '75%' :
                      selectedFile ? '100%' : '90%'
                    }`
                  }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 配置查询条件 */}
      {selectedFile && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
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
                {conditions.map((condition) => {
                  if (!condition.value) return null;
                  const indicator = getSelectedIndicator(condition.field);
                  const displayName = indicator?.indicator_name || condition.field;
                  return (
                    <Badge key={condition.id} variant="outline" className="mr-2">
                      {displayName} {condition.operator} {condition.value}
                    </Badge>
                  );
                })}
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
              {conditions.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  暂无查询条件，点击"添加条件"开始配置
                </div>
              )}

              {conditions.map((condition, index) => (
                <div key={condition.id} className="flex gap-2 items-end">
                  <div className="flex-1">
                    <Label className="text-sm text-muted-foreground">指标字段</Label>
                    <Select
                      value={condition.field}
                      onValueChange={(value) => updateCondition(condition.id, 'field', value)}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="选择指标" />
                      </SelectTrigger>
                      <SelectContent>
                        {indicators.map((indicator) => (
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
                  </div>

                  {condition.field && (
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

                  {condition.field && (
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

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeCondition(condition.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
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
                  disabled={querying || conditions.filter(c => c.field && c.value).length === 0}
                  className="w-32"
                >
                  {querying ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      查询中...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4 mr-2" />
                      查询
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* 查询结果 */}
      {(queryResult || querying) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                查询结果
                {querying && <Loader2 className="w-4 h-4 animate-spin" />}
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                {querying ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    正在查询数据...
                  </div>
                ) : queryResult ? (
                  `共 ${queryResult.total} 条记录，当前显示第 ${queryResult.page} 页`
                ) : null}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {querying ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <div className="text-center space-y-2">
                  <div className="text-lg font-medium">正在查询数据</div>
                  <div className="text-sm text-muted-foreground">
                    请稍候，正在处理您的查询请求...
                  </div>
                </div>
              </div>
            ) : queryResult && queryResult.items.length > 0 ? (
              <>
                {/* 数据表格 */}
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {Object.keys(queryResult.items[0]).map((key) => (
                          <TableHead key={key} className="whitespace-nowrap">{key}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {queryResult.items.map((row, rowIndex) => (
                        <TableRow key={rowIndex}>
                          {Object.values(row).map((value: unknown, idx: number) => (
                            <TableCell key={idx} className="whitespace-nowrap">
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
                            onClick={() => !querying && executeQuery(currentPage - 1)}
                            className={cn(
                              currentPage === 1 || querying ? "pointer-events-none opacity-50" : "cursor-pointer",
                              querying && "cursor-not-allowed"
                            )}
                          />
                        </PaginationItem>

                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          const page = i + 1;
                          return (
                            <PaginationItem key={page}>
                              <PaginationLink
                                onClick={() => !querying && executeQuery(page)}
                                isActive={page === currentPage}
                                className={cn(
                                  "cursor-pointer",
                                  querying && "cursor-not-allowed opacity-50"
                                )}
                              >
                                {querying && page === currentPage ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  page
                                )}
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
                            onClick={() => !querying && executeQuery(currentPage + 1)}
                            className={cn(
                              currentPage === totalPages || querying ? "pointer-events-none opacity-50" : "cursor-pointer",
                              querying && "cursor-not-allowed"
                            )}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                    
                    {/* 分页信息 */}
                    <div className="mt-2 text-center text-sm text-muted-foreground">
                      {querying ? (
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          正在加载第 {currentPage} 页...
                        </div>
                      ) : (
                        `第 ${currentPage} 页，共 ${totalPages} 页`
                      )}
                    </div>
                  </div>
                )}
              </>
            ) : queryResult && queryResult.items.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <div className="flex flex-col items-center gap-4">
                  <Search className="w-12 h-12 opacity-50" />
                  <div className="space-y-2">
                    <div className="text-lg font-medium">没有找到符合条件的数据</div>
                    <div className="text-sm">
                      请尝试调整查询条件或选择其他数据文件
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
