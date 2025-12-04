"use client";

import React, { useEffect, useRef } from "react";
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

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new messages arrive or processing state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  return (
    <>
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
    </>
  );
}