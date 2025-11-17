"use client";

import React from "react";
import { Bot } from "lucide-react";

export function WelcomeMessage() {
  return (
    <div className="text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary text-primary-foreground shadow-md mb-4">
        <Bot className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold mb-2">欢迎使用淘沙 Agent</h3>
      <p className="text-muted-foreground">我是您的智能助手，可以帮助您进行数据分析和问答</p>
    </div>
  );
}