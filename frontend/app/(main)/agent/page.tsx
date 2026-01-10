"use client";

import { AgentProvider } from "@/lib/state/agent";
import { ChatSidebarLayout } from "@/components/agent/ChatSidebar";
import { ChatMessagesArea } from "@/components/agent/ChatMessagesArea";
import { ChatInput } from "@/components/agent/ChatInput";
import { useAgentState } from "@/lib/state/agent";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

function AgentPageContent() {
  const { sendMessage, isProcessing } = useAgentState();
  const { user } = useAuth();

  return (
    <>
      {/* 消息区域 - 独立滚动 */}
      <Card className="flex-1 flex flex-col overflow-hidden border shadow-sm">
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          <ChatMessagesArea />
        </CardContent>
      </Card>

      {/* 输入框 - 固定在底部，不在滚动区域内 */}
      <ChatInput onSendMessage={sendMessage} disabled={isProcessing} />
    </>
  );
}

export default function Page() {
  const { user } = useAuth();

  // 确保用户已认证
  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-muted-foreground">正在加载用户信息...</p>
        </div>
      </div>
    );
  }

  return (
    <AgentProvider userId={user.user_id}>
      <ChatSidebarLayout>
        <AgentPageContent />
      </ChatSidebarLayout>
    </AgentProvider>
  );
}