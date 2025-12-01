"use client";

import React, { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { useAgentState } from "@/lib/state/agent";
import { MessageItem } from "./MessageItem";
import { WelcomeMessage } from "./WelcomeMessage";
import { ProcessingIndicator } from "./ProcessingIndicator";

export function ChatMessagesArea() {
  const {
    messages,
    isProcessing,
    processingText,
  } = useAgentState();

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new messages arrive or processing state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  return (
    <Card className="flex-1 border-0 shadow-sm">
      <CardContent className="p-0 h-full">
        <ScrollArea ref={scrollAreaRef} className="h-full">
          <div className="p-6 space-y-4">
            {/* Welcome Message */}
            {messages.length === 0 && <WelcomeMessage />}

            {/* Messages */}
            {messages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
              />
            ))}

            {/* Processing Indicator */}
            {isProcessing && (
              <ProcessingIndicator processingText={processingText} />
            )}

            {/* Bottom anchor for auto-scroll */}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}