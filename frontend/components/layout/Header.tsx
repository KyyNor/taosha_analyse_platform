"use client";
import Link from "next/link";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "../ui/dropdown-menu";

type NavItem = {
  type: 'link';
  href: string;
  label: string;
} | {
  type: 'dropdown';
  label: string;
  items: Array<{ href: string; label: string }>;
};

const navItems: NavItem[] = [
  { type: 'link', href: "/nlquery", label: "查询" },
  { type: 'link', href: "/agent", label: "Agent" },
  { type: 'link', href: "/history", label: "历史" },
  { type: 'link', href: "/favorites", label: "收藏" },
  { type: 'link', href: "/settings", label: "设置" },
  {
    type: 'dropdown',
    label: "猎诈",
    items: [
      { href: "/fraudhunter/indicator-tasks", label: "指标任务" },
      { href: "/fraudhunter/indicators", label: "指标" },
      { href: "/fraudhunter/dry-run", label: "试运行详情" }
    ]
  },
  {
    type: 'dropdown',
    label: "元数据",
    items: [
      { href: "/metadata/tables", label: "数据表" },
      { href: "/metadata/relations", label: "关系" },
      { href: "/metadata/glossary", label: "术语表" },
      { href: "/metadata/themes", label: "主题" },
      { href: "/metadata/prompt-templates", label: "提示模板" }
    ]
  }
];

export default function Header() {
  // 为每个dropdown维护独立的开关状态
  const [openDropdowns, setOpenDropdowns] = useState<Record<string, boolean>>({});

  const handleDropdownChange = (label: string, isOpen: boolean) => {
    setOpenDropdowns(prev => ({ ...prev, [label]: isOpen }));
  };

  const renderNavItem = (item: NavItem) => {
    if (item.type === 'link') {
      return (
        <Link
          key={item.href}
          href={item.href}
          className="text-muted-foreground hover:text-foreground"
        >
          {item.label}
        </Link>
      );
    }

    // type === 'dropdown'
    const isOpen = openDropdowns[item.label] || false;
    return (
      <DropdownMenu
        key={item.label}
        open={isOpen}
        onOpenChange={(open) => handleDropdownChange(item.label, open)}
      >
        <DropdownMenuTrigger asChild>
          <button
            onMouseEnter={() => handleDropdownChange(item.label, true)}
            className="text-muted-foreground hover:text-foreground"
          >
            {item.label}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          onMouseEnter={() => handleDropdownChange(item.label, true)}
          onMouseLeave={() => handleDropdownChange(item.label, false)}
          align="end"
          className="min-w-[12rem] bg-background border border-solid"
        >
          {item.items.map((subItem) => (
            <DropdownMenuItem key={subItem.href} asChild>
              <Link href={subItem.href}>{subItem.label}</Link>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-screen-2xl px-6 h-14 flex items-center justify-between">
        <Link href="/nlquery" className="font-semibold">淘沙分析平台</Link>
        <nav className="flex items-center gap-4 text-sm">
          {navItems.map((item) => renderNavItem(item))}
        </nav>
      </div>
    </header>
  );
}