"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Copy, Check } from "lucide-react";
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { alertControlRecordService } from "@/lib/services/fraudhunter/alertControlRecordService";
import type { AlertControlRecordDetail } from "@/lib/services/fraudhunter/alertControlRecordService";

export default function AlertControlRecordDetailPage() {
  const router = useRouter();
  const params = useParams();
  const recordId = Number(params?.id || 0);

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AlertControlRecordDetail | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await alertControlRecordService.get(recordId);
      setData(result);
    } catch (error) {
      console.error("Failed to load alert control record:", error);
      toast.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [recordId]);

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

  // 状态标签渲染
  const renderStatusBadge = (status: string, type: 'alert' | 'control') => {
    const statusConfig = {
      not_configured: { 
        variant: "secondary" as const, 
        label: type === 'alert' ? "未配置告警" : "未配置管控" 
      },
      sent: { variant: "default" as const, label: "已发送" },
      executed: { variant: "default" as const, label: "已执行" },
      duplicate: { variant: "outline" as const, label: type === 'alert' ? "重复告警" : "重复管控" }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || {
      variant: "secondary" as const,
      label: status
    };

    return (
      <Badge variant={config.variant}>
        {config.label}
      </Badge>
    );
  };

  // 格式化日期时间
  const formatDateTime = (dateTimeStr?: string) => {
    if (!dateTimeStr) return "-";
    const date = new Date(dateTimeStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN');
  };

  // 复制按钮组件
  const CopyButton = ({ text, fieldName }: { text: string; fieldName: string }) => (
    <Button
      variant="ghost"
      size="sm"
      className="h-6 w-6 p-0 ml-2"
      onClick={() => copyToClipboard(text, fieldName)}
    >
      {copiedField === fieldName ? (
        <Check className="h-3 w-3 text-green-600" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </Button>
  );

  // 信息行组件
  const InfoRow = ({ 
    label, 
    value, 
    copyable = false, 
    copyValue 
  }: { 
    label: string; 
    value: React.ReactNode; 
    copyable?: boolean; 
    copyValue?: string; 
  }) => (
    <div className="flex justify-between items-start py-2">
      <span className="text-sm font-medium text-muted-foreground min-w-[100px]">
        {label}:
      </span>
      <div className="flex items-center flex-1 justify-end">
        <span className="text-sm text-right">{value}</span>
        {copyable && copyValue && (
          <CopyButton text={copyValue} fieldName={label} />
        )}
      </div>
    </div>
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
        <div className="text-center">记录不存在</div>
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
            onClick={() => router.push("/fraudhunter/alert-control-records")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <h1 className="text-2xl font-bold">告警管控记录详情</h1>
          <Badge variant="outline">ID: {data.record.id}</Badge>
        </div>
      </div>

      <div className="space-y-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <InfoRow 
              label="记录ID" 
              value={data.record.id} 
              copyable 
              copyValue={String(data.record.id)} 
            />
            <InfoRow 
              label="账号" 
              value={<span className="font-mono">{data.record.account_id}</span>} 
              copyable 
              copyValue={data.record.account_id} 
            />
            <InfoRow 
              label="记录日期" 
              value={formatDate(data.record.record_date)} 
            />
            <InfoRow 
              label="创建时间" 
              value={formatDateTime(data.record.created_at)} 
            />
            <InfoRow 
              label="更新时间" 
              value={formatDateTime(data.record.updated_at)} 
            />
          </CardContent>
        </Card>

        {/* 模型信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">模型信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <InfoRow 
              label="模型ID" 
              value={data.record.model_id} 
              copyable 
              copyValue={String(data.record.model_id)} 
            />
            <InfoRow 
              label="模型名称" 
              value={data.record.model_name} 
              copyable 
              copyValue={data.record.model_name} 
            />
          </CardContent>
        </Card>

        {/* 告警信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">告警信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <InfoRow 
              label="告警状态" 
              value={renderStatusBadge(data.record.alert_status, 'alert')} 
            />
            {data.record.alert_message && (
              <div className="py-2">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-sm font-medium text-muted-foreground">
                    告警消息:
                  </span>
                  <CopyButton text={data.record.alert_message} fieldName="告警消息" />
                </div>
                <div className="bg-muted p-3 rounded-md text-sm">
                  {data.record.alert_message}
                </div>
              </div>
            )}
            <InfoRow 
              label="告警人" 
              value={data.record.alert_person || "-"} 
            />
            <InfoRow 
              label="告警时间" 
              value={formatDateTime(data.record.alert_time)} 
            />
          </CardContent>
        </Card>

        {/* 管控信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">管控信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <InfoRow 
              label="管控状态" 
              value={renderStatusBadge(data.record.control_status, 'control')} 
            />
            <InfoRow 
              label="管控时间" 
              value={formatDateTime(data.record.control_time)} 
            />
            <InfoRow 
              label="管控流水号" 
              value={data.record.control_serial_number || "-"} 
              copyable={!!data.record.control_serial_number}
              copyValue={data.record.control_serial_number} 
            />
          </CardContent>
        </Card>

        {/* 关联命中记录 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">关联命中记录</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <InfoRow 
              label="命中记录ID" 
              value={data.hit_record.id} 
              copyable 
              copyValue={String(data.hit_record.id)} 
            />
            <InfoRow 
              label="命中时间" 
              value={formatDateTime(data.hit_record.hit_time)} 
            />
            <InfoRow 
              label="命中模型数量" 
              value={data.hit_record.hit_model_ids.length} 
            />
            
            {/* 命中模型列表 */}
            <div className="py-2">
              <span className="text-sm font-medium text-muted-foreground">
                命中模型列表:
              </span>
              <div className="mt-2 space-y-2">
                {data.hit_record.hit_model_ids.map((modelId, index) => (
                  <div key={modelId} className="flex items-center justify-between bg-muted p-2 rounded">
                    <span className="text-sm">
                      {data.hit_record.hit_model_names[index] || `模型 ${modelId}`}
                    </span>
                    <Badge variant="outline">ID: {modelId}</Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* 指标数据 */}
            <div className="py-2">
              <div className="flex justify-between items-start mb-2">
                <span className="text-sm font-medium text-muted-foreground">
                  指标数据:
                </span>
                <CopyButton 
                  text={JSON.stringify(data.hit_record.indicator_data, null, 2)} 
                  fieldName="指标数据" 
                />
              </div>
              <div className="bg-muted p-3 rounded-md">
                <pre className="text-xs overflow-x-auto">
                  {JSON.stringify(data.hit_record.indicator_data, null, 2)}
                </pre>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}