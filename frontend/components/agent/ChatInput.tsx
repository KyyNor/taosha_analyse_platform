"use client";

import React, { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { InputGroup, InputGroupButton } from "@/components/ui/input-group";
import { Send, Trash2 } from "lucide-react";
import { useAgentState } from "@/lib/state/agent";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [inputMessage, setInputMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { clearMessages } = useAgentState();

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputMessage(e.target.value);
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  const handleSend = useCallback(() => {
    if (inputMessage.trim() && !disabled) {
      onSendMessage(inputMessage.trim());
      setInputMessage("");
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [inputMessage, onSendMessage, disabled]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        return;
      } else {
        // Send message with Enter
        e.preventDefault();
        handleSend();
      }
    }
  }, [handleSend]);

  const handleClear = useCallback(() => {
    if (confirm('确定要清空所有对话记录吗？此操作无法撤销。')) {
      clearMessages();
    }
  }, [clearMessages]);

  return (
    <div className="border-t bg-background p-4">
      <InputGroup className="min-h-0">
        <Textarea
          ref={textareaRef}
          value={inputMessage}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="输入您的问题..."
          className="resize-none border-0 shadow-none focus-visible:ring-0 min-h-0 max-h-32"
          rows={1}
        />
        <div className="flex gap-2 p-2">
          <InputGroupButton
            onClick={handleSend}
            disabled={!inputMessage.trim() || disabled}
            title="发送消息 (Enter)"
          >
            <Send className="w-4 h-4" />
          </InputGroupButton>

          <InputGroupButton
            variant="outline"
            onClick={handleClear}
            disabled={disabled}
            title="清空对话"
          >
            <Trash2 className="w-4 h-4" />
          </InputGroupButton>
        </div>
      </InputGroup>

      <div className="text-xs text-muted-foreground mt-2 ml-1">
        按 Enter 发送，Shift + Enter 换行
      </div>
    </div>
  );
}