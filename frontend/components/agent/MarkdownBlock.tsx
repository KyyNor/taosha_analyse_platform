"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";

interface MarkdownBlockProps {
  content: string;
  className?: string;
}

export function MarkdownBlock({ content, className }: MarkdownBlockProps) {
  return (
    <div className={cn("prose prose-sm max-w-none dark:prose-invert", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !className?.includes('language-') && !match;
            return !isInline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus as any}
                language={match[1]}
                PreTag="div"
                className="rounded-md"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code
                className="px-1 py-0.5 rounded text-sm font-mono bg-accent text-accent-foreground"
                {...props}
              >
                {children}
              </code>
            );
          }
        }}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  );
}
