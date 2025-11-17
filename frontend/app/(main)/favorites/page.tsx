"use client";
import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getFavorites, executeFavorite, updateFavorite, deleteFavorite } from "@/lib/services/favoritesService";
import { toast } from "@/components/ui/sonner";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<any | null>(null);
  const [title, setTitle] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await getFavorites(1, 50);
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

  const onExecute = async (id: number) => {
    try {
      await executeFavorite(id);
      toast.success("已执行收藏查询");
    } catch {
      toast.error("执行失败");
    }
  };

  const onEdit = (item: any) => {
    setCurrentItem(item);
    setTitle(String(item?.title ?? ""));
    setEditOpen(true);
  };

  const onSave = async () => {
    if (!currentItem) return;
    try {
      await updateFavorite(Number(currentItem.id), title.trim());
      toast.success("收藏已更新");
      setEditOpen(false);
      setCurrentItem(null);
      await load();
    } catch {
      toast.error("更新失败");
    }
  };

  const onDelete = async (id: number) => {
    try {
      await deleteFavorite(id);
      toast.success("收藏已删除");
      await load();
    } catch {
      toast.error("删除失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Input placeholder="搜索收藏..." value={q} onChange={(e) => setQ(e.target.value)} />
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
                  <TableCell className="px-3 py-2 flex gap-2">
                    {row.id ? (
                      <>
                        <Button size="sm" variant="outline" onClick={() => onExecute(Number(row.id))}>执行</Button>
                        <Button size="sm" variant="outline" onClick={() => onEdit(row)}>编辑</Button>
                        <Button size="sm" variant="destructive" onClick={() => onDelete(Number(row.id))}>删除</Button>
                      </>
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
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑收藏</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditOpen(false)}>取消</Button>
              <Button onClick={onSave}>保存</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}