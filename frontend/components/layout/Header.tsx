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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { useMemo, useState } from "react";
import { User, Building, Shield } from "lucide-react";

type NavItem = {
  type: 'link';
  href: string;
  label: string;
  requiresAdmin?: boolean;
} | {
  type: 'dropdown';
  label: string;
  requiresAdmin?: boolean;
  items: Array<
    | { type: 'link'; href: string; label: string; requiresAdmin?: boolean }
    | { type: 'separator' }
    | { type: 'group'; label: string }
  >;
};

// 完整的导航菜单配置，包含所有功能
const allNavItems: NavItem[] = [
  { type: 'link', href: "/agent", label: "Agent" },
  { type: 'link', href: "/deepagents", label: "DeepAgents" },
  {
    type: 'dropdown',
    label: "猎诈",
    items: [
      { type: 'group', label: "指标管理" },
      { type: 'link', href: "/fraudhunter/indicators", label: "指标定义" },
      { type: 'link', href: "/fraudhunter/indicator-tasks", label: "指标任务" },
      { type: 'link', href: "/fraudhunter/indicator-query", label: "指标数据查询" },
      { type: 'separator' },
      { type: 'group', label: "模型管理" },
      { type: 'link', href: "/fraudhunter/risk-control-models", label: "预警管控模型定义" },
      { type: 'link', href: "/fraudhunter/alert-control-records", label: "模型预警记录" },
      { type: 'separator' },
      { type: 'group', label: "试运行" },
      { type: 'link', href: "/fraudhunter/dry-run", label: "试运行详情" },
      { type: 'separator' },
      { type: 'group', label: "系统管理" },
      { type: 'link', href: "/fraudhunter/system-config", label: "系统配置" },
      { type: 'link', href: "/fraudhunter/wide-table-versions", label: "指标宽表版本" },
    ]
  },
  {
    type: 'dropdown',
    label: "元数据",
    items: [
      { type: 'link', href: "/metadata/tables", label: "数据表" },
      { type: 'link', href: "/metadata/relations", label: "关系" },
      { type: 'link', href: "/metadata/glossary", label: "术语表" },
      { type: 'link', href: "/metadata/prompt-templates", label: "提示模板" },
      { type: 'link', href: "/metadata/fine-reports", label: "帆软报表" }
    ]
  },
  {
    type: 'dropdown',
    label: "系统管理",
    requiresAdmin: true,
    items: [
      { type: 'group', label: "权限管理" },
      { type: 'link', href: "/admin/departments", label: "部门管理", requiresAdmin: true },
      { type: 'link', href: "/admin/roles", label: "角色管理", requiresAdmin: true },
      { type: 'link', href: "/admin/permissions", label: "权限分配", requiresAdmin: true },
      { type: 'separator' },
      { type: 'group', label: "系统监控" },
      { type: 'link', href: "/admin/login-records", label: "登录记录", requiresAdmin: true }
    ]
  }
];

// 用户信息弹出组件
function UserInfoPopover({ user }: { user: { user_name: string; user_id: string; branch_no: string; branch_name: string; role_name_list: string[] } }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          className="h-9 px-3 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
          onMouseEnter={() => setIsOpen(true)}
          onMouseLeave={() => setIsOpen(false)}
        >
          <User className="mr-2 h-4 w-4" />
          {user.user_name}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-80"
        align="end"
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
      >
        <div className="space-y-4">
          {/* 用户基本信息 */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{user.user_name}</span>
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <span className="font-medium">OA号:</span>
              <span>{user.user_id}</span>
            </div>
          </div>

          {/* 机构信息 */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Building className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">机构信息</span>
            </div>
            <div className="space-y-1 text-sm text-muted-foreground pl-6">
              <div className="flex items-center space-x-2">
                <span className="font-medium">机构号:</span>
                <span>{user.branch_no}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="font-medium">机构名:</span>
                <span>{user.branch_name}</span>
              </div>
            </div>
          </div>

          {/* 角色列表 */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">角色列表</span>
            </div>
            <div className="flex flex-wrap gap-2 pl-6">
              {user.role_name_list.map((role) => (
                <Badge key={role} variant="secondary" className="text-xs">
                  {role}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default function Header() {
  const { isAuthenticated, isAdmin, user } = useAuth();
  const visibleNavItems = useMemo(() => {
    return allNavItems.filter(item => {
      // 如果菜单项需要管理员权限但用户不是管理员，则隐藏
      if (item.requiresAdmin && !isAdmin) {
        return false;
      }
      
      // 对于下拉菜单，需要过滤其子项
      if (item.type === 'dropdown') {
        const visibleSubItems = item.items.filter(subItem => {
          // 分隔符和分组标题总是显示
          if (subItem.type === 'separator' || subItem.type === 'group') {
            return true;
          }
          
          // 链接项需要检查权限
          if (subItem.type === 'link') {
            return !subItem.requiresAdmin || isAdmin;
          }
          
          return true;
        });
        
        // 如果过滤后没有可见的链接项，则隐藏整个下拉菜单
        const hasVisibleLinks = visibleSubItems.some(subItem => subItem.type === 'link');
        if (!hasVisibleLinks) {
          return false;
        }
        
        // 返回过滤后的下拉菜单
        return {
          ...item,
          items: visibleSubItems
        };
      }
      
      return true;
    }).map(item => {
      // 对于下拉菜单，应用子项过滤
      if (item.type === 'dropdown') {
        const visibleSubItems = item.items.filter(subItem => {
          if (subItem.type === 'separator' || subItem.type === 'group') {
            return true;
          }
          if (subItem.type === 'link') {
            return !subItem.requiresAdmin || isAdmin;
          }
          return true;
        });
        
        return {
          ...item,
          items: visibleSubItems
        };
      }
      
      return item;
    });
  }, [isAdmin]);
  
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
            {item.items.map((subItem, index) => {
              // 处理分隔符
              if (subItem.type === 'separator') {
                return (
                  <li key={`separator-${index}`} className="my-1">
                    <div className="h-px bg-border" />
                  </li>
                );
              }

              // 处理分组标题
              if (subItem.type === 'group') {
                return (
                  <li key={`group-${index}`} className="px-3 pt-2 pb-1">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {subItem.label}
                    </div>
                  </li>
                );
              }

              // 处理链接
              return (
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
              );
            })}
          </ul>
        </NavigationMenuContent>
      </NavigationMenuItem>
    );
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-screen-2xl px-6 h-14 flex items-center justify-between">
        <Link href="/agent" className="font-semibold text-lg">淘沙分析平台</Link>
        <div className="flex items-center gap-4">
          <NavigationMenu>
            <NavigationMenuList className="flex items-center gap-1">
              {visibleNavItems.map((item) => renderNavItem(item))}
            </NavigationMenuList>
          </NavigationMenu>
          {isAuthenticated && user && <UserInfoPopover user={user} />}
        </div>
      </div>
    </header>
  );
}