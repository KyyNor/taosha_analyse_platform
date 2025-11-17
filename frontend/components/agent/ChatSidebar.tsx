"use client";

import React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
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
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Brain, Wrench, Sparkles, MessageSquare, Settings, Plus } from "lucide-react";
import { useAgentState } from "@/lib/state/agent";
import { cn } from "@/lib/utils";

// 需要添加 Switch 组件
export function ChatSidebar() {
  const {
    sidebarOpen,
    showThinkingChain,
    showToolCalls,
    toggleThinkingChain,
    toggleToolCalls,
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            <span className="font-semibold">智能对话</span>
          </div>
          <Badge variant="secondary" className="text-xs">
            {hasMessages ? "进行中" : "新对话"}
          </Badge>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>当前对话</SidebarGroupLabel>
          <SidebarGroupContent>
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
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>历史对话</SidebarGroupLabel>
          <SidebarGroupContent>
            <div className="text-center py-4 text-muted-foreground text-sm">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>暂无历史对话</p>
              <p className="text-xs mt-1">功能开发中...</p>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>显示设置</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton className="px-2 py-1.5">
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <Brain className="w-4 h-4" />
                      <span className="text-sm">思维链</span>
                    </div>
                    <Switch
                      checked={showThinkingChain}
                      onCheckedChange={toggleThinkingChain}
                    />
                  </div>
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton className="px-2 py-1.5">
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <Wrench className="w-4 h-4" />
                      <span className="text-sm">工具调用</span>
                    </div>
                    <Switch
                      checked={showToolCalls}
                      onCheckedChange={toggleToolCalls}
                    />
                  </div>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>高级功能</SidebarGroupLabel>
          <SidebarGroupContent>
            <Button
              variant="outline"
              className="w-full justify-start text-sm h-8"
              disabled
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Generative UI
              <Badge variant="secondary" className="ml-auto text-xs">
                即将推出
              </Badge>
            </Button>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <Button
          variant="ghost"
          className="w-full justify-start text-sm h-8"
          disabled
        >
          <Settings className="w-4 h-4 mr-2" />
          设置
        </Button>
      </SidebarFooter>
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