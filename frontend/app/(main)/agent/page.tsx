"use client";

import { AgentProvider } from "@/lib/state/agent";
import { ChatSidebarLayout } from "@/components/agent/ChatSidebar";
import { ChatMessagesArea } from "@/components/agent/ChatMessagesArea";
import { ChatInput } from "@/components/agent/ChatInput";
import { useAgentState } from "@/lib/state/agent";
import { Card, CardContent } from "@/components/ui/card";

function AgentPageContent() {
  const { sendMessage, isProcessing } = useAgentState();

  return (
    <>
      {/* 消息区域 - 独立滚动 */}
      <Card className="flex-1 flex flex-col overflow-hidden border shadow-sm">
        <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
          <ChatMessagesArea />
        </CardContent>
      </Card>

      {/* 输入框 - 固定在底部，不在滚动区域内 */}
      <ChatInput onSendMessage={sendMessage} disabled={isProcessing} />
    </>
  );
}

export default function Page() {
  return (
    <AgentProvider>
      <ChatSidebarLayout>
        <AgentPageContent />
      </ChatSidebarLayout>
    </AgentProvider>
  );
}