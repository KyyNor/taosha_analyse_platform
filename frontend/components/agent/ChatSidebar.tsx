"use client";

import React from "react";
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
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useAgentState } from "@/lib/state/agent";
import { cn } from "@/lib/utils";

export function ChatSidebar() {
  const {
    sidebarOpen,
    setSidebarOpen,
    hasMessages,
    sessions,
    currentSessionId,
    switchSession,
    deleteSession,
    createNewSession,
  } = useAgentState();

  const { open, setOpen } = useSidebar();

  // 同步sidebar状态
  React.useEffect(() => {
    setOpen(sidebarOpen);
  }, [sidebarOpen, setOpen]);

  React.useEffect(() => {
    setSidebarOpen(open);
  }, [open, setSidebarOpen]);

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            <span className="font-semibold">对话历史</span>
          </div>
          <Button variant="ghost" size="icon" onClick={createNewSession} title="新对话">
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
                <SidebarMenuButton onClick={createNewSession} isActive={!currentSessionId}>
                  <Plus className="w-4 h-4" />
                  <span>开始新对话</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
             </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>历史对话</SidebarGroupLabel>
          <SidebarGroupContent>
            {sessions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
                <p>暂无历史对话</p>
              </div>
            ) : (
              <SidebarMenu>
                {sessions.map((session) => (
                  <SidebarMenuItem key={session.id}>
                    <SidebarMenuButton
                      onClick={() => switchSession(session.id)}
                      isActive={currentSessionId === session.id}
                      className="group flex justify-between items-center"
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <MessageSquare className="w-4 h-4 shrink-0" />
                        <span className="truncate">{session.title || "未命名会话"}</span>
                      </div>
                      <div 
                        className={cn(
                          "opacity-0 group-hover:opacity-100 transition-opacity",
                          currentSessionId === session.id ? "opacity-100" : ""
                        )}
                        onClick={(e) => {
                          e.stopPropagation();
                          if(confirm('确认删除此会话吗？')) {
                            deleteSession(session.id);
                          }
                        }}
                      >
                        <Trash2 className="w-3 h-3 hover:text-destructive" />
                      </div>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}

// 主聊天布局容器
export function ChatSidebarLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <ChatSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            <h1 className="text-lg font-semibold">智能助手</h1>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}