"use client";
import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { getTables } from "@/lib/services/metadataService";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const [q, setQ] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await getTables();
      setData(Array.isArray(res?.data) ? res.data : res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return data;
    return data.filter((row: any) => {
      return Object.values(row ?? {}).some((v) => String(v ?? "").toLowerCase().includes(t));
    });
  }, [q, data]);

  const columns = useMemo(() => Object.keys(filtered[0] ?? {}), [filtered]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Input placeholder="搜索..." value={q} onChange={(e) => setQ(e.target.value)} />
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
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((row, i) => (
                <TableRow key={i}>
                  {columns.map((c) => (
                    <TableCell key={c} className="px-3 py-2">{String(row[c])}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {!loading && filtered.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">暂无数据</div>
        ) : null}
      </div>
    </div>
  );
}