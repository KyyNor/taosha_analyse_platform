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
    <div className="p-4 bg-background/50 backdrop-blur-sm">
      <div className="max-w-4xl mx-auto">
        <InputGroup className="min-h-0 bg-white dark:bg-secondary/20 shadow-lg border rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 transition-all">
          <Textarea
            ref={textareaRef}
            value={inputMessage}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="输入您的问题..."
            className="resize-none border-0 shadow-none focus-visible:ring-0 min-h-[50px] max-h-32 py-3 bg-transparent"
            rows={1}
          />
          <div className="flex gap-2 p-2 self-end">
            <InputGroupButton
              variant="ghost"
              onClick={handleClear}
              disabled={disabled}
              title="清空对话"
              className="text-muted-foreground hover:text-destructive transition-colors hover:bg-destructive/10"
            >
              <Trash2 className="w-4 h-4" />
            </InputGroupButton>
            
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!inputMessage.trim() || disabled}
              title="发送消息 (Enter)"
              className="h-8 w-8 rounded-lg shadow-sm transition-all"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </InputGroup>

        <div className="text-xs text-muted-foreground mt-2 ml-1 text-center opacity-70">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </div>
  );
}