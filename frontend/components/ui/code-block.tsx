"use client"

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"
import { cn } from "@/lib/utils"

interface CodeBlockProps {
  /** 代码内容 */
  code: string
  /** 语法语言，默认 sql */
  language?: string
  className?: string
}

/**
 * 只读代码高亮展示块，基于 react-syntax-highlighter (Prism)。
 * 复用 components/agent/MarkdownBlock.tsx 的 vscDarkPlus 主题以保持视觉一致。
 */
export function CodeBlock({ code, language = "sql", className }: CodeBlockProps) {
  return (
    <div className={cn("mt-1 overflow-hidden rounded-md", className)}>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus as any}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: "0.75rem",
          fontSize: "0.875rem",
          background: "hsl(var(--muted))",
        }}
        codeTagProps={{
          style: {
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          },
        }}
        wrapLongLines
      >
        {code ?? ""}
      </SyntaxHighlighter>
    </div>
  )
}
