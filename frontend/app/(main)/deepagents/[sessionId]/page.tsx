"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Download,
  Copy,
  Check,
  FileText,
  BarChart3,
  MessageSquare,
  RefreshCw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

import { deepagentsService } from "@/lib/services/deepagentsService";
import type {
  SessionDetailResponse,
  AnalysisScore,
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

// 获取评分颜色
const getScoreColor = (score: number | null) => {
  if (score === null) return "text-muted-foreground";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
};

export default function DeepAgentsDetailPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.sessionId as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SessionDetailResponse | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const result = await deepagentsService.getSession(sessionId);
      setData(result);
    } catch (error) {
      console.error("Failed to load session:", error);
      toast.error("加载失败");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 定时刷新（如果任务在运行中）
  useEffect(() => {
    if (
      data?.session.status === "running" ||
      data?.session.status === "pending"
    ) {
      const interval = setInterval(loadData, 5000);
      return () => clearInterval(interval);
    }
  }, [data?.session.status, loadData]);

  // 复制到剪贴板
  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      toast.success("已复制到剪贴板");
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      toast.error("复制失败");
    }
  };

  // 下载
  const handleDownload = async () => {
    setDownloading(true);
    try {
      await deepagentsService.downloadOutput(sessionId);
      toast.success("下载已开始");
    } catch (error) {
      console.error("Download failed:", error);
      toast.error("下载失败");
    } finally {
      setDownloading(false);
    }
  };

  // 渲染评分卡片
  const renderScoreCard = (
    title: string,
    score: number | null,
    reasons: string[] | null,
    deductions: string[] | null
  ) => (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center justify-between">
          {title}
          <span className={`text-2xl font-bold ${getScoreColor(score)}`}>
            {score ?? "-"}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {reasons && reasons.length > 0 && (
          <div>
            <div className="text-sm font-medium text-green-600 mb-1">优点</div>
            <ul className="text-sm space-y-1">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-green-600">+</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {deductions && deductions.length > 0 && (
          <div>
            <div className="text-sm font-medium text-red-600 mb-1">扣分项</div>
            <ul className="text-sm space-y-1">
              {deductions.map((d, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-red-600">-</span>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {(!reasons || reasons.length === 0) &&
          (!deductions || deductions.length === 0) && (
            <div className="text-sm text-muted-foreground">暂无详细评分</div>
          )}
      </CardContent>
    </Card>
  );

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
        <div className="text-center">会话不存在</div>
      </div>
    );
  }

  const { session, scores } = data;
  const status = statusConfig[session.status] || statusConfig.pending;

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={() => router.push("/deepagents")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold">分析详情</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-muted-foreground font-mono">
                {session.session_id.slice(0, 8)}...
              </span>
              <Badge variant={status.variant}>{status.label}</Badge>
              {scores?.overall_score !== null && scores?.overall_score !== undefined && (
                <Badge variant="outline">综合评分: {scores.overall_score}</Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={loadData}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          {session.report_path && (
            <Button onClick={handleDownload} disabled={downloading}>
              <Download className="h-4 w-4 mr-2" />
              {downloading ? "下载中..." : "下载结果"}
            </Button>
          )}
        </div>
      </div>

      <Tabs defaultValue="info" className="space-y-4">
        <TabsList>
          <TabsTrigger value="info">
            <FileText className="h-4 w-4 mr-2" />
            基本信息
          </TabsTrigger>
          <TabsTrigger value="scores">
            <BarChart3 className="h-4 w-4 mr-2" />
            评分详情
          </TabsTrigger>
          <TabsTrigger value="output">
            <MessageSquare className="h-4 w-4 mr-2" />
            LLM输出
          </TabsTrigger>
        </TabsList>

        {/* 基本信息 */}
        <TabsContent value="info" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">任务信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">会话ID</div>
                  <div className="font-mono text-sm flex items-center gap-2">
                    {session.session_id}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() =>
                        copyToClipboard(session.session_id, "session_id")
                      }
                    >
                      {copiedField === "session_id" ? (
                        <Check className="h-3 w-3 text-green-600" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">问题来源</div>
                  <div>{session.question_source || "manual"}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">开始时间</div>
                  <div>{formatDateTime(session.start_time)}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">结束时间</div>
                  <div>{formatDateTime(session.end_time)}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">执行耗时</div>
                  <div>{formatDuration(session.duration_seconds)}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">报告路径</div>
                  <div className="font-mono text-sm truncate">
                    {session.report_path || "-"}
                  </div>
                </div>
              </div>
              <Separator />
              <div>
                <div className="text-sm text-muted-foreground mb-2">
                  分析问题
                </div>
                <div className="bg-muted p-4 rounded-md">{session.question}</div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 评分详情 */}
        <TabsContent value="scores" className="space-y-4">
          {scores ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {renderScoreCard(
                  "分析过程",
                  scores.process_score,
                  scores.process_reasons,
                  scores.process_deductions
                )}
                {renderScoreCard(
                  "分析报告",
                  scores.report_score,
                  scores.report_reasons,
                  scores.report_deductions
                )}
                {renderScoreCard(
                  "分析结论",
                  scores.conclusion_score,
                  scores.conclusion_reasons,
                  scores.conclusion_deductions
                )}
              </div>

              {/* 改进建议 */}
              {scores.improvement_suggestions &&
                scores.improvement_suggestions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">改进建议</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {scores.improvement_suggestions.map((s, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-3 p-3 bg-muted rounded-md"
                          >
                            <Badge variant="outline">{s.priority}</Badge>
                            <Badge variant="secondary">{s.category}</Badge>
                            <span className="text-sm">{s.suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}
            </>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                暂无评分数据
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* LLM输出 */}
        <TabsContent value="output">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                大模型输出
                {session.llm_output && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      copyToClipboard(session.llm_output || "", "llm_output")
                    }
                  >
                    {copiedField === "llm_output" ? (
                      <Check className="h-4 w-4 mr-2" />
                    ) : (
                      <Copy className="h-4 w-4 mr-2" />
                    )}
                    复制
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {session.llm_output ? (
                <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-md max-h-[600px] overflow-auto">
                  {session.llm_output}
                </pre>
              ) : (
                <div className="py-8 text-center text-muted-foreground">
                  暂无LLM输出内容
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
