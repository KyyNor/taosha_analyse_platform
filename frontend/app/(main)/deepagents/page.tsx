"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, RefreshCw, Search, Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { deepagentsService } from "@/lib/services/deepagentsService";
import type {
  SessionListItem,
  QueueStatus,
} from "@/lib/services/deepagentsService";

// 状态配置
const statusConfig: Record<
  string,
  { variant: "default" | "secondary" | "destructive" | "outline"; label: string }
> = {
  pending: { variant: "secondary", label: "等待中" },
  running: { variant: "default", label: "执行中" },
  completed: { variant: "outline", label: "已完成" },
  failed: { variant: "destructive", label: "失败" },
};

// 评分颜色
const getScoreColor = (score: number | null) => {
  if (score === null) return "text-muted-foreground";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
};

// 格式化时间
const formatDateTime = (dateTimeStr: string | null) => {
  if (!dateTimeStr) return "-";
  return new Date(dateTimeStr).toLocaleString("zh-CN");
};

// 格式化耗时
const formatDuration = (seconds: number | null) => {
  if (seconds === null) return "-";
  if (seconds < 60) return `${seconds.toFixed(1)}秒`;
  return `${(seconds / 60).toFixed(1)}分钟`;
};

export default function DeepAgentsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SessionListItem[]>([]);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 筛选状态
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // 新建对话框
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [newQuestion, setNewQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sessionsRes, statusRes] = await Promise.all([
        deepagentsService.listSessions({
          page: currentPage,
          page_size: pageSize,
          status: statusFilter !== "all" ? statusFilter : undefined,
          search: searchQuery.trim() || undefined,
        }),
        deepagentsService.getQueueStatus(),
      ]);

      setData(sessionsRes.items);
      setTotal(sessionsRes.total);
      setQueueStatus(statusRes);
    } catch (error) {
      console.error("Failed to load data:", error);
      toast.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, statusFilter, searchQuery]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 定时刷新队列状态
  useEffect(() => {
    const interval = setInterval(() => {
      deepagentsService
        .getQueueStatus()
        .then(setQueueStatus)
        .catch(console.error);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // 提交新任务
  const handleSubmit = async () => {
    if (!newQuestion.trim()) {
      toast.error("请输入分析问题");
      return;
    }

    setSubmitting(true);
    try {
      const result = await deepagentsService.submitTask({
        question: newQuestion.trim(),
        question_source: "manual",
      });

      toast.success(`任务已提交: ${result.session_id.slice(0, 8)}...`);
      setNewDialogOpen(false);
      setNewQuestion("");
      loadData();
    } catch (error) {
      console.error("Submit failed:", error);
      toast.error("提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  // 搜索处理
  const handleSearch = () => {
    setCurrentPage(1);
    loadData();
  };

  // 总页数
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面标题 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">DeepAgents 数据分析</h1>
          <p className="text-muted-foreground">
            AI驱动的自动化数据分析任务管理
          </p>
        </div>
        <Button onClick={() => setNewDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          新建分析
        </Button>
      </div>

      {/* 队列状态卡片 */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            队列状态
            <Button variant="ghost" size="sm" onClick={loadData}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">运行状态:</span>
              <Badge variant={queueStatus?.is_running ? "default" : "secondary"}>
                {queueStatus?.is_running ? "运行中" : "已停止"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">等待任务:</span>
              <span className="font-medium">{queueStatus?.queue_size || 0}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">执行中:</span>
              <span className="font-medium">{queueStatus?.running_count || 0}</span>
            </div>
            {queueStatus?.current_task && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">当前任务:</span>
                <span className="font-mono text-sm">
                  {queueStatus.current_task.session_id.slice(0, 8)}...
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 筛选区域 */}
      <div className="mb-4 flex items-center gap-4">
        <div className="flex-1 flex items-center gap-2">
          <Input
            placeholder="搜索分析问题..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="max-w-sm"
          />
          <Button variant="outline" size="icon" onClick={handleSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
        <Select value={statusFilter} onValueChange={(v) => {
          setStatusFilter(v);
          setCurrentPage(1);
        }}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="pending">等待中</SelectItem>
            <SelectItem value="running">执行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 数据表格 */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">ID</TableHead>
              <TableHead>分析问题</TableHead>
              <TableHead className="w-24">状态</TableHead>
              <TableHead className="w-20">评分</TableHead>
              <TableHead className="w-40">开始时间</TableHead>
              <TableHead className="w-24">耗时</TableHead>
              <TableHead className="w-20">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center py-8 text-muted-foreground"
                >
                  暂无分析任务
                </TableCell>
              </TableRow>
            ) : (
              data.map((item) => {
                const status = statusConfig[item.status] || statusConfig.pending;
                return (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono">{item.id}</TableCell>
                    <TableCell className="max-w-md truncate">
                      {item.question}
                    </TableCell>
                    <TableCell>
                      <Badge variant={status.variant}>{status.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <span className={getScoreColor(item.overall_score)}>
                        {item.overall_score !== null ? item.overall_score : "-"}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDateTime(item.start_time)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDuration(item.duration_seconds)}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          router.push(`/deepagents/${item.session_id}`)
                        }
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <div className="text-sm text-muted-foreground">
              共 {total} 条记录，第 {currentPage} / {totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* 新建对话框 */}
      <Dialog open={newDialogOpen} onOpenChange={setNewDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>新建数据分析任务</DialogTitle>
            <DialogDescription>
              输入您想要分析的问题，AI将自动进行数据查询、分析和报告生成
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="question">分析问题</Label>
            <Textarea
              id="question"
              placeholder="例如: 分析近三个月的销售趋势，找出增长最快的产品类别"
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              rows={4}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "提交中..." : "提交任务"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
