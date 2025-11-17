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
import { MessageSquare } from "lucide-react";
import { useAgentState } from "@/lib/state/agent";

export function ChatSidebar() {
  const {
    sidebarOpen,
    setSidebarOpen,
    hasMessages,
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
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          <span className="font-semibold">对话历史</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>当前对话</SidebarGroupLabel>
          <SidebarGroupContent>
            {hasMessages && (
              <Card className="bg-primary/5 border-primary/20">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    对话会话
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  当前正在进行的智能对话
                </CardContent>
              </Card>
            )}
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>历史对话</SidebarGroupLabel>
          <SidebarGroupContent>
            <div className="text-center py-8 text-muted-foreground text-sm">
              <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p>暂无历史对话</p>
              <p className="text-xs mt-1 opacity-70">功能开发中...</p>
            </div>
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