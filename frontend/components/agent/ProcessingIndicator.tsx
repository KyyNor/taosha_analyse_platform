"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Bot } from "lucide-react";

interface ProcessingIndicatorProps {
  processingText: string;
}

export function ProcessingIndicator({ processingText }: ProcessingIndicatorProps) {
  return (
    <div className="flex gap-3 justify-start">
      <div className="flex-shrink-0">
        <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-md">
          <Bot className="w-4 h-4" />
        </div>
      </div>
      <Card className="bg-muted text-muted-foreground border-0 shadow-md">
        <CardContent className="p-3">
          <div className="flex items-center gap-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span className="text-sm">{processingText}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}