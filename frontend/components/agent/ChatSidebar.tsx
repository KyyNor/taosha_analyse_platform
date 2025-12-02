"use client";

import React, { useMemo } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageSquare, Plus, Trash2, Clock } from "lucide-react";
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

  const { setOpenMobile } = useSidebar();

  // 分组会话
  const sessionGroups = useMemo(() => groupSessions(sessions), [sessions]);

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            <span className="font-semibold">对话历史</span>
          </div>
          <Button variant="ghost" size="icon" onClick={() => {
            createNewSession();
            setOpenMobile(false);
          }} title="新对话">
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* 当前活动会话卡片 - 仅在没有历史记录或当前是新会话时显示一种状态 */}
        <SidebarGroup>
          <SidebarGroupLabel>操作</SidebarGroupLabel>
          <SidebarGroupContent>
             <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton onClick={() => {
                  createNewSession();
                  setOpenMobile(false);
                }} isActive={!currentSessionId}>
                  <Plus className="w-4 h-4" />
                  <span>开始新对话</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
             </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* 历史对话分组 */}
        {sessions.length === 0 ? (
          <SidebarGroup>
            <SidebarGroupLabel>历史对话</SidebarGroupLabel>
            <SidebarGroupContent>
              <div className="text-center py-8 text-muted-foreground text-sm">
                <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
                <p>暂无历史对话</p>
              </div>
            </SidebarGroupContent>
          </SidebarGroup>
        ) : (
          sessionGroups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.sessions.map((session) => (
                    <SidebarMenuItem key={session.id}>
                      <SidebarMenuButton
                        onClick={() => {
                          switchSession(session.id);
                          setOpenMobile(false);
                        }}
                        isActive={currentSessionId === session.id}
                        className={cn(
                          "group flex flex-col items-start py-3 h-auto transition-all duration-200 hover:translate-x-1",
                          currentSessionId === session.id 
                            ? "bg-sidebar-accent shadow-sm border border-sidebar-border/50" 
                            : "hover:bg-sidebar-accent/50"
                        )}
                      >
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center gap-2 overflow-hidden flex-1">
                            <MessageSquare className={cn(
                              "w-4 h-4 shrink-0 transition-colors",
                              currentSessionId === session.id ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                            )} />
                            <span className={cn(
                              "truncate font-medium transition-colors",
                              currentSessionId === session.id ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                            )}>{session.title || "未命名会话"}</span>
                          </div>
                          <div
                            className={cn(
                              "opacity-0 group-hover:opacity-100 transition-opacity shrink-0 p-1 rounded-md hover:bg-background",
                              currentSessionId === session.id ? "opacity-100" : ""
                            )}
                            onClick={(e) => {
                              e.stopPropagation();
                              if(confirm('确认删除此会话吗？')) {
                                deleteSession(session.id);
                              }
                            }}
                          >
                            <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive transition-colors" />
                          </div>
                        </div>
                        <div className="flex items-center gap-1 text-[10px] text-muted-foreground/70 mt-1.5 ml-6">
                          <Clock className="w-3 h-3" />
                          <span>{formatTime(session.updated_at)}</span>
                        </div>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>
    </Sidebar>
  );
}

// 主聊天布局容器
export function ChatSidebarLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider defaultOpen={false}>
      <ChatSidebar />
      <SidebarInset className="h-full overflow-hidden bg-slate-50 dark:bg-slate-950">
        {/* Floating Sidebar Trigger */}
        <div className="absolute top-4 left-4 z-20">
          <SidebarTrigger className="h-10 w-10 rounded-full shadow-md bg-white dark:bg-zinc-800 border hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all text-primary" />
        </div>
        
        {/* Main Content Area */}
        <div className="flex flex-1 flex-col h-full w-full relative">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}