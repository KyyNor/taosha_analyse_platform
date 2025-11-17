"use client";
import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getQueryHistory, getQueryHistoryDetail } from "@/lib/services/historyService";
import { toast } from "sonner";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLogs, setDetailLogs] = useState<any[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getQueryHistory(1, 50, {});
      setItems(res?.data ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return items;
    return items.filter((row: any) => {
      return Object.values(row ?? {}).some((v) => String(v ?? "").toLowerCase().includes(t));
    });
  }, [q, items]);

  const columns = useMemo(() => Object.keys(filtered[0] ?? {}), [filtered]);

  const openDetail = async (taskId: string) => {
    setCurrentTaskId(taskId);
    try {
      const res = await getQueryHistoryDetail(taskId);
      setDetailLogs(res?.data ?? []);
      setDetailOpen(true);
    } catch {
      toast.error("加载详情失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Input placeholder="搜索历史..." value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant="outline" onClick={load} disabled={loading}>刷新</Button>
      </div>
      <div className="rounded-md border">
        {loading ? (
          <div className="p-4 text-sm text-muted-foreground">加载中...</div>
        ) : (
          <Table className="min-w-full text-sm">
            <TableHeader>
              <TableRow>
                {columns.map((c) => (
                  <TableHead key={c} className="px-3 py-2 text-left">{c}</TableHead>
                ))}
                <TableHead className="px-3 py-2 text-left">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((row: any, i: number) => (
                <TableRow key={i}>
                  {columns.map((c) => (
                    <TableCell key={c} className="px-3 py-2">{String(row[c])}</TableCell>
                  ))}
                  <TableCell className="px-3 py-2">
                    {row.task_id ? (
                      <Button size="sm" variant="outline" onClick={() => openDetail(row.task_id)}>详情</Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {!loading && filtered.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">暂无数据</div>
        ) : null}
      </div>
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>任务详情 {currentTaskId ?? ""}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {detailLogs.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无日志</div>
            ) : (
              detailLogs.map((log, idx) => (
                <pre key={idx} className="rounded-md border bg-muted/30 p-3 text-xs whitespace-pre-wrap">
                  {JSON.stringify(log, null, 2)}
                </pre>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}