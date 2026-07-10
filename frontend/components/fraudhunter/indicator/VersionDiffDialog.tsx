"use client";

import { useEffect, useState, useMemo } from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { indicatorTaskService } from "@/lib/services/fraudhunterService";
import type { IndicatorTaskVersionHistory } from "@/lib/services/fraudhunterService";

interface VersionDiffDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskId: number;
  /** 当前任务的最新版本号，用于默认选中 */
  latestVersion: number;
}

/**
 * 指标任务版本对比对话框。
 * 左右并排展示两个版本的差异，支持切换对比版本和对比字段（离线SQL/实时SQL/描述等）。
 */
export function VersionDiffDialog({
  open,
  onOpenChange,
  taskId,
  latestVersion,
}: VersionDiffDialogProps) {
  const [versions, setVersions] = useState<IndicatorTaskVersionHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [leftVersion, setLeftVersion] = useState<number>(-1);
  const [rightVersion, setRightVersion] = useState<number>(-1);

  // 拉取版本历史
  useEffect(() => {
    if (!open || !taskId) return;

    let cancelled = false;
    setLoading(true);
    indicatorTaskService
      .getVersionHistory(taskId)
      .then((res) => {
        if (cancelled) return;
        const items = res.items || [];
        setVersions(items);
        // 默认对比最新版本与上一版本
        // 后端按 created_at desc 返回，即 items[0] 是最新
        if (items.length >= 2) {
          setLeftVersion(items[1].version);
          setRightVersion(items[0].version);
        } else if (items.length === 1) {
          setLeftVersion(items[0].version);
          setRightVersion(items[0].version);
        }
      })
      .catch(() => {
        if (!cancelled) setVersions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, taskId]);

  const leftItem = useMemo(
    () => versions.find((v) => v.version === leftVersion),
    [versions, leftVersion]
  );
  const rightItem = useMemo(
    () => versions.find((v) => v.version === rightVersion),
    [versions, rightVersion]
  );

  const diffStyles = {
    variables: {
      dark: {
        diffViewerBackground: "hsl(var(--muted))",
        gutterBackground: "hsl(var(--muted))",
      },
      light: {
        diffViewerBackground: "hsl(var(--muted))",
        gutterBackground: "hsl(var(--muted))",
      },
    },
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>版本对比</DialogTitle>
          <DialogDescription>
            对比指标任务不同版本之间的差异（左右并排展示）
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">加载版本历史...</span>
          </div>
        ) : versions.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            暂无版本历史记录
          </div>
        ) : versions.length === 1 ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            仅有一个版本（v{versions[0].version}），无法进行对比
          </div>
        ) : (
          <div className="flex flex-col gap-4 min-h-0 flex-1">
            {/* 版本选择器 */}
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">旧版本</span>
                <Select
                  value={String(leftVersion)}
                  onValueChange={(v) => setLeftVersion(Number(v))}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={String(v.version)}>
                        v{v.version}
                        <span className="text-muted-foreground ml-1">
                          ({v.change_type})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <span className="text-muted-foreground">→</span>

              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">新版本</span>
                <Select
                  value={String(rightVersion)}
                  onValueChange={(v) => setRightVersion(Number(v))}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={String(v.version)}>
                        v{v.version}
                        <span className="text-muted-foreground ml-1">
                          ({v.change_type})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 版本元信息 */}
            {leftItem && rightItem && (
              <div className="flex gap-3 text-xs text-muted-foreground">
                <Badge variant="outline">
                  旧版 v{leftItem.version}: {leftItem.change_description || leftItem.change_type}
                </Badge>
                <Badge variant="outline">
                  新版 v{rightItem.version}: {rightItem.change_description || rightItem.change_type}
                </Badge>
              </div>
            )}

            {/* 分字段对比 */}
            <Tabs defaultValue="logic_content" className="min-h-0 flex-1 flex flex-col">
              <TabsList className="self-start">
                <TabsTrigger value="logic_content">离线SQL</TabsTrigger>
                <TabsTrigger value="realtime_logic_content">实时SQL</TabsTrigger>
                <TabsTrigger value="description">描述</TabsTrigger>
                <TabsTrigger value="source_tables">依赖源表</TabsTrigger>
              </TabsList>

              <TabsContent value="logic_content" className="overflow-auto min-h-0 flex-1">
                {leftItem && rightItem && (
                  <ReactDiffViewer
                    oldValue={leftItem.logic_content || ""}
                    newValue={rightItem.logic_content || ""}
                    splitView
                    compareMethod={DiffMethod.WORDS}
                    styles={diffStyles}
                    hideLineNumbers={false}
                  />
                )}
              </TabsContent>

              <TabsContent value="realtime_logic_content" className="overflow-auto min-h-0 flex-1">
                {leftItem && rightItem && (
                  <ReactDiffViewer
                    oldValue={leftItem.realtime_logic_content || ""}
                    newValue={rightItem.realtime_logic_content || ""}
                    splitView
                    compareMethod={DiffMethod.WORDS}
                    styles={diffStyles}
                    hideLineNumbers={false}
                  />
                )}
              </TabsContent>

              <TabsContent value="description" className="overflow-auto min-h-0 flex-1">
                {leftItem && rightItem && (
                  <ReactDiffViewer
                    oldValue={leftItem.description || ""}
                    newValue={rightItem.description || ""}
                    splitView
                    compareMethod={DiffMethod.WORDS}
                    styles={diffStyles}
                    hideLineNumbers={false}
                  />
                )}
              </TabsContent>

              <TabsContent value="source_tables" className="overflow-auto min-h-0 flex-1">
                {leftItem && rightItem && (
                  <ReactDiffViewer
                    oldValue={leftItem.source_tables || ""}
                    newValue={rightItem.source_tables || ""}
                    splitView
                    compareMethod={DiffMethod.WORDS}
                    styles={diffStyles}
                    hideLineNumbers={false}
                  />
                )}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
