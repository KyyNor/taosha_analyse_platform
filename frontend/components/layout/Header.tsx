'use client'

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Database,
  BookOpen,
  GitBranch,
  MessageSquare,
  Palette,
  Bot,
  ChevronDown
} from "lucide-react"

export default function Header() {
  return (
    <header className="border-b bg-white">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link href="/" className="text-xl font-bold text-gray-900">
              淘沙分析平台
            </Link>
          </div>

          {/* 主导航 */}
          <nav className="flex items-center space-x-4">
            {/* 淘沙Agent 按钮 */}
            <Link href="/agent">
              <Button
                variant="ghost"
                className="flex items-center space-x-2 hover:bg-indigo-50 hover:text-indigo-600"
              >
                <Bot className="h-4 w-4" />
                <span>淘沙Agent</span>
              </Button>
            </Link>

            {/* 元数据下拉菜单 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex items-center space-x-2 hover:bg-blue-50 hover:text-blue-600"
                >
                  <Database className="h-4 w-4" />
                  <span>元数据</span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem asChild>
                  <Link href="/metadata/tables" className="flex items-center space-x-2">
                    <Database className="h-4 w-4" />
                    <span>表元数据</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/metadata/glossary" className="flex items-center space-x-2">
                    <BookOpen className="h-4 w-4" />
                    <span>业务术语</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/metadata/relations" className="flex items-center space-x-2">
                    <GitBranch className="h-4 w-4" />
                    <span>关联配置</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/metadata/prompts" className="flex items-center space-x-2">
                    <MessageSquare className="h-4 w-4" />
                    <span>提示词配置</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/metadata/themes" className="flex items-center space-x-2">
                    <Palette className="h-4 w-4" />
                    <span>数据主题</span>
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>
        </div>
      </div>
    </header>
  )
}