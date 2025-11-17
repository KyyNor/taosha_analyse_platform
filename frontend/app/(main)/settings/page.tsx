"use client";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export default function Page() {
  const [apiBase, setApiBase] = useState<string>(process.env.NEXT_PUBLIC_API_BASE || "/api");
  const [wsBase, setWsBase] = useState<string>(process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:50020/ws");
  const [notes, setNotes] = useState<string>("");

  const save = async () => {
    // 预留：可接入后端设置保存接口或写入浏览器存储
    console.log("save", { apiBase, wsBase, notes });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <label className="text-sm">API 基础路径</label>
        <Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
      </div>
      <div className="space-y-3">
        <label className="text-sm">WebSocket 基础路径</label>
        <Input value={wsBase} onChange={(e) => setWsBase(e.target.value)} />
      </div>
      <div className="space-y-3">
        <label className="text-sm">备注</label>
        <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      <div className="flex gap-2">
        <Button variant="outline">重置</Button>
        <Button onClick={save}>保存</Button>
      </div>
    </div>
  );
}