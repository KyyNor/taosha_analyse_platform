"use client";
import Link from "next/link";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "../ui/dropdown-menu";

const items = [
  { href: "/nlquery", label: "查询" },
  { href: "/agent", label: "Agent" },
  { href: "/history", label: "日志" },
  { href: "/favorites", label: "收藏" },
  { href: "/settings", label: "设置" }
];

export default function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
        <Link href="/nlquery" className="font-semibold">淘沙分析平台</Link>
        <nav className="flex items-center gap-4 text-sm">
          {items.map((i) => (
            <Link key={i.href} href={i.href} className="text-muted-foreground hover:text-foreground">
              {i.label}
            </Link>
          ))}
          <DropdownMenu open={open} onOpenChange={setOpen}>
            <DropdownMenuTrigger asChild>
              <button
                onMouseEnter={() => setOpen(true)}
                className="text-muted-foreground hover:text-foreground"
              >
                元数据
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              onMouseEnter={() => setOpen(true)}
              onMouseLeave={() => setOpen(false)}
              align="end"
              className="min-w-[12rem]"
            >
              <DropdownMenuItem asChild>
                <Link href="/metadata/tables">数据表</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/metadata/relations">关系</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/metadata/glossary">术语表</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/metadata/themes">主题</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/metadata/prompt-templates">提示模板</Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </div>
    </header>
  );
}