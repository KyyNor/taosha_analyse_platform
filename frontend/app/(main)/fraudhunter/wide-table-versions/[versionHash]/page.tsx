"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Clock, XCircle } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell
} from "@/components/ui/table";
import { wideTableVersionService } from "@/lib/services/fraudhunterService";
import type { WideTableVersionDetail, WideTableVersionProgress } from "@/lib/services/fraudhunterService";

export default function WideTableVersionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const versionHash = params.versionHash as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<WideTableVersionDetail | null>(null);
  const [progressData, setProgressData] = useState<WideTableVersionProgress | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  // 加载详情数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await wideTableVersionService.getDetail(versionHash);
      setData(result);
    } catch (error: any) {
      console.error("Failed to load version detail:", error);
      toast.error("加载版本详情失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载进度数据
  const loadProgress = async () => {
    try {
      const result = await wideTableVersionService.getProgress(versionHash, 30);
      setProgressData(result);
    } catch (error: any) {
      console.error("Failed to load progress:", error);
    }
  };

  useEffect(() => {
    if (versionHash) {
      loadData();
      loadProgress();
    }
  }, [versionHash]);

  // 获取状态Badge
  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      current: "default",
      target: "secondary",
      history: "outline",
      skipped: "destructive"
    };
    const labels: Record<string, string> = {
      current: "当前版本",
      target: "目标版本",
      history: "历史版本",
      skipped: "已跳过"
    };
    return <Badge variant={variants[status] || "default"}>{labels[status] || status}</Badge>;
  };

  // 获取宽表名称显示
  const getTableNameLabel = (name: string) => {
    const labels: Record<string, string> = {
      dep_acct_wide_table: "存款账户宽表",
      cust_wide_table: "客户宽表",
      loan_acct_wide_table: "贷款账户宽表"
    };
    return labels[name] || name;
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container mx-auto py-6">
        <div className="text-center">版本不存在</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push("/fraudhunter/wide-table-versions")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {getTableNameLabel(data.wide_table_name)}
              {getStatusBadge(data.status)}
            </h1>
            <p className="text-muted-foreground">
              版本号: <code className="bg-muted px-2 py-1 rounded">{data.version_hash}</code>
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={() => { loadData(); loadProgress(); }}>
          刷新
        </Button>
      </div>

      {/* 标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="indicators">指标清单 ({data.indicators.length})</TabsTrigger>
          <TabsTrigger value="progress">执行进度</TabsTrigger>
        </TabsList>

        {/* 概览标签 */}
        <TabsContent value="overview">
          <div className="grid gap-6 md:grid-cols-2">
            {/* 基本信息 */}
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">宽表名称</label>
                    <p className="font-medium">{getTableNameLabel(data.wide_table_name)}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">状态</label>
                    <p>{getStatusBadge(data.status)}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">指标数量</label>
                    <p className="font-medium">{data.indicators.length} 个</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">快照数量</label>
                    <p className="font-medium">{data.snapshot_count} 个</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">创建时间</label>
                    <p className="text-sm">{new Date(data.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">创建人</label>
                    <p className="text-sm">{data.created_by || '-'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 状态时间线 */}
            <Card>
              <CardHeader>
                <CardTitle>状态变更</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.target_at && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">
                        成为目标版本: {new Date(data.target_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {data.current_at && (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      <span className="text-sm">
                        成为当前版本: {new Date(data.current_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {data.history_at && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">
                        成为历史版本: {new Date(data.history_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {data.skipped_at && (
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-destructive" />
                      <span className="text-sm">
                        被跳过: {new Date(data.skipped_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 执行进度概览 */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>已完成的ETL日期</CardTitle>
                <CardDescription>
                  共 {data.completed_dates.length} 个日期已完成执行
                </CardDescription>
              </CardHeader>
              <CardContent>
                {data.completed_dates.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {data.completed_dates.slice(0, 20).map((date) => (
                      <Badge key={date} variant="outline" className="bg-green-50 text-green-700">
                        {date}
                      </Badge>
                    ))}
                    {data.completed_dates.length > 20 && (
                      <Badge variant="secondary">
                        +{data.completed_dates.length - 20} 更多
                      </Badge>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground">暂无已完成的ETL日期</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 指标清单标签 */}
        <TabsContent value="indicators">
          <Card>
            <CardHeader>
              <CardTitle>指标清单</CardTitle>
              <CardDescription>
                该版本包含的所有指标定义
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>指标ID</TableHead>
                      <TableHead>指标编码</TableHead>
                      <TableHead>指标名称</TableHead>
                      <TableHead>指标类型</TableHead>
                      <TableHead>版本号</TableHead>
                      <TableHead>指标任务ID</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.indicators.length > 0 ? (
                      data.indicators.map((indicator) => (
                        <TableRow key={indicator.indicator_id}>
                          <TableCell>{indicator.indicator_id}</TableCell>
                          <TableCell>
                            <code className="bg-muted px-2 py-1 rounded text-xs">
                              {indicator.indicator_code}
                            </code>
                          </TableCell>
                          <TableCell>{indicator.indicator_name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {indicator.indicator_type === 'offline' ? '离线' : '实时'}
                            </Badge>
                          </TableCell>
                          <TableCell>v{indicator.indicator_version}</TableCell>
                          <TableCell>
                            {indicator.indicator_task_id ? (
                              <Button
                                variant="link"
                                size="sm"
                                className="p-0 h-auto"
                                onClick={() => router.push(`/fraudhunter/indicator-tasks/${indicator.indicator_task_id}`)}
                              >
                                {indicator.indicator_task_id}
                              </Button>
                            ) : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground">
                          暂无指标数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 执行进度标签 */}
        <TabsContent value="progress">
          <Card>
            <CardHeader>
              <CardTitle>执行进度详情</CardTitle>
              <CardDescription>
                最近30天的ETL执行情况
              </CardDescription>
            </CardHeader>
            <CardContent>
              {progressData && progressData.recent_progress.length > 0 ? (
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ETL日期</TableHead>
                        <TableHead>完成指标数</TableHead>
                        <TableHead>总指标数</TableHead>
                        <TableHead>完成状态</TableHead>
                        <TableHead>最后完成时间</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {progressData.recent_progress.map((progress) => (
                        <TableRow key={progress.etl_date}>
                          <TableCell className="font-medium">{progress.etl_date}</TableCell>
                          <TableCell>{progress.completed_count}</TableCell>
                          <TableCell>{progress.total_count}</TableCell>
                          <TableCell>
                            {progress.is_complete ? (
                              <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                已完成
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-orange-600">
                                <Clock className="h-3 w-3 mr-1" />
                                进行中 ({Math.round(progress.completed_count / progress.total_count * 100)}%)
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {progress.last_finish_time
                              ? new Date(progress.last_finish_time).toLocaleString()
                              : '-'
                            }
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">
                  暂无执行进度数据
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}