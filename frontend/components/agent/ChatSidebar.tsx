"use client";

import React, { useMemo, useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageSquare, Plus, Trash2, Clock, Menu } from "lucide-react";
import { useAgentState } from "@/lib/state/agent";
import { cn } from "@/lib/utils";
import type { Session } from "@/lib/api";

// 时间格式化工具函数
function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor(diff / (1000 * 60));

  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;

  // 超过7天显示具体日期
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
}

// 会话分组类型
interface SessionGroup {
  label: string;
  sessions: Session[];
}

// 分组会话
function groupSessions(sessions: Session[]): SessionGroup[] {
  const now = new Date();
  const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  const recent: Session[] = [];
  const older: Session[] = [];

  sessions.forEach(session => {
    const sessionDate = new Date(session.updated_at);
    if (sessionDate >= oneWeekAgo) {
      recent.push(session);
    } else {
      older.push(session);
    }
  });

  const groups: SessionGroup[] = [];
  if (recent.length > 0) {
    groups.push({ label: "最近", sessions: recent });
  }
  if (older.length > 0) {
    groups.push({ label: "一周之前", sessions: older });
  }

  return groups;
}

export function ChatSidebar() {
  const {
    sessions,
    currentSessionId,
    switchSession,
    deleteSession,
    createNewSession,
  } = useAgentState();

  // 分组会话
  const sessionGroups = useMemo(() => groupSessions(sessions), [sessions]);

  return (
    <>
      <CardHeader className="shrink-0 border-b p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            <span className="font-semibold">对话历史</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={createNewSession}
            title="新对话"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4">
        {/* 操作：开始新对话 */}
        <div className="mb-4">
          <Button
            variant={!currentSessionId ? "secondary" : "outline"}
            size="sm"
            onClick={createNewSession}
            className="w-full justify-start"
          >
            <Plus className="w-4 h-4 mr-2" />
            <span>开始新对话</span>
          </Button>
        </div>

        {/* 历史对话列表 */}
        {sessions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
            <p>暂无历史对话</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sessionGroups.map((group) => (
              <div key={group.label} className="space-y-2">
                <h3 className="text-xs font-medium text-muted-foreground px-2">
                  {group.label}
                </h3>
                <div className="space-y-1">
                  {group.sessions.map((session) => (
                    <div
                      key={session.id}
                      onClick={() => switchSession(session.id)}
                      className={cn(
                        "group flex flex-col p-3 rounded-md cursor-pointer",
                        "transition-all duration-200 hover:translate-x-1",
                        currentSessionId === session.id
                          ? "bg-secondary shadow-sm border border-border"
                          : "hover:bg-secondary/50"
                      )}
                    >
                      <div className="flex items-center justify-between w-full">
                        <div className="flex items-center gap-2 overflow-hidden flex-1">
                          <MessageSquare
                            className={cn(
                              "w-4 h-4 shrink-0 transition-colors",
                              currentSessionId === session.id
                                ? "text-primary"
                                : "text-muted-foreground group-hover:text-foreground"
                            )}
                          />
                          <span
                            className={cn(
                              "truncate font-medium transition-colors text-sm",
                              currentSessionId === session.id
                                ? "text-foreground"
                                : "text-muted-foreground group-hover:text-foreground"
                            )}
                          >
                            {session.title || "未命名会话"}
                          </span>
                        </div>
                        <button
                          className={cn(
                            "opacity-0 group-hover:opacity-100 transition-opacity",
                            "shrink-0 p-1 rounded-md hover:bg-background",
                            currentSessionId === session.id ? "opacity-100" : ""
                          )}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("确认删除此会话吗？")) {
                              deleteSession(session.id);
                            }
                          }}
                        >
                          <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive transition-colors" />
                        </button>
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-muted-foreground/70 mt-1.5 ml-6">
                        <Clock className="w-3 h-3" />
                        <span>{formatTime(session.updated_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </>
  );
}

// 主聊天布局容器
export function ChatSidebarLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 默认折叠

  return (
    <div className="flex gap-4 min-h-[600px] max-h-[calc(100vh-12rem)]">
      {/* 左侧历史面板 - 条件渲染 */}
      {isSidebarOpen && (
        <aside className="w-64 shrink-0 flex flex-col">
          <Card className="flex-1 flex flex-col overflow-hidden border shadow-sm">
            <ChatSidebar />
          </Card>
        </aside>
      )}

      {/* 右侧聊天区域 */}
      <main className="flex-1 min-w-0 flex flex-col gap-4">
        {/* 折叠按钮 */}
        <div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            <Menu className="w-4 h-4 mr-2" />
            {isSidebarOpen ? "隐藏历史" : "显示历史"}
          </Button>
        </div>

        {children}
      </main>
    </div>
  );
}