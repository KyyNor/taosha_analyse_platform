"use client";

import { AgentProvider } from "@/lib/state/agent";
import { ChatSidebarLayout } from "@/components/agent/ChatSidebar";
import { ChatMessagesArea } from "@/components/agent/ChatMessagesArea";
import { ChatInput } from "@/components/agent/ChatInput";
import { AgentTestDemo } from "@/components/agent/AgentTestDemo";
import { useAgentState } from "@/lib/state/agent";

function AgentPageContent() {
  const { sendMessage, isProcessing } = useAgentState();

  return (
    <div className="flex flex-col h-full">
      {/* Test Demo (仅开发阶段) */}
      <AgentTestDemo />

      {/* Chat Messages Area */}
      <div className="flex-1">
        <ChatMessagesArea />
      </div>

      {/* Chat Input */}
      <ChatInput onSendMessage={sendMessage} disabled={isProcessing} />
    </div>
  );
}

export default function Page() {
  return (
    <AgentProvider>
      <div className="h-screen flex flex-col">
        <ChatSidebarLayout>
          <AgentPageContent />
        </ChatSidebarLayout>
      </div>
    </AgentProvider>
  );
}