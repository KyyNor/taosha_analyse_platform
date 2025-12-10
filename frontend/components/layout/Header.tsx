"use client";
import Link from "next/link";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import { cn } from "@/lib/utils";

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
      { href: "/fraudhunter/dry-run", label: "试运行详情" },
      { href: "/fraudhunter/risk-control-models", label: "预警管控模型" },
      { href: "/fraudhunter/wide-table-versions", label: "指标宽表版本" }
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
  const renderNavItem = (item: NavItem) => {
    if (item.type === 'link') {
      return (
        <NavigationMenuItem key={item.href}>
          <Link href={item.href} legacyBehavior passHref>
            <NavigationMenuLink className={cn(navigationMenuTriggerStyle(), "text-muted-foreground hover:text-foreground")}>
              {item.label}
            </NavigationMenuLink>
          </Link>
        </NavigationMenuItem>
      );
    }

    // type === 'dropdown'
    return (
      <NavigationMenuItem key={item.label}>
        <NavigationMenuTrigger>{item.label}</NavigationMenuTrigger>
        <NavigationMenuContent>
          <ul className="grid gap-3 p-4 w-[200px] md:w-[300px]">
            {item.items.map((subItem) => (
              <li key={subItem.href}>
                <Link href={subItem.href} legacyBehavior passHref>
                  <NavigationMenuLink
                    className={cn(
                      "block select-none space-y-1 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                    )}
                  >
                    <div className="text-sm font-medium leading-none">{subItem.label}</div>
                  </NavigationMenuLink>
                </Link>
              </li>
            ))}
          </ul>
        </NavigationMenuContent>
      </NavigationMenuItem>
    );
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-screen-2xl px-6 h-14 flex items-center justify-between">
        <Link href="/nlquery" className="font-semibold text-lg">淘沙分析平台</Link>
        <NavigationMenu>
          <NavigationMenuList className="flex items-center gap-1">
            {navItems.map((item) => renderNavItem(item))}
          </NavigationMenuList>
        </NavigationMenu>
      </div>
    </header>
  );
}