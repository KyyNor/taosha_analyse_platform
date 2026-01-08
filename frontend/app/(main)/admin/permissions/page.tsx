"use client";

import { useRequireAdmin } from "@/hooks/useAuth";
import { Shield } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import PermissionsByEntityView from "@/components/admin/permissions/PermissionsByEntityView";
import PermissionsByPageView from "@/components/admin/permissions/PermissionsByPageView";
import UserPermissionsQueryView from "@/components/admin/permissions/UserPermissionsQueryView";

export default function PermissionsPage() {
  const { isAuthenticated, isLoading, isAdmin } = useRequireAdmin();

  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <p className="text-muted-foreground">验证权限中...</p>
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return null;
  }

  return (
    <div className="container mx-auto py-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="h-6 w-6" />
          权限分配
        </h1>
        <p className="text-muted-foreground">为部门和角色分配页面访问权限</p>
      </div>

      {/* Tab切换三个视图 */}
      <Tabs defaultValue="by-entity" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="by-entity" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            按实体配置
          </TabsTrigger>
          <TabsTrigger value="by-page" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            按页面配置
          </TabsTrigger>
          <TabsTrigger value="user-permissions" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            用户权限查询
          </TabsTrigger>
        </TabsList>

        <TabsContent value="by-entity" className="mt-4">
          <PermissionsByEntityView />
        </TabsContent>

        <TabsContent value="by-page" className="mt-4">
          <PermissionsByPageView />
        </TabsContent>

        <TabsContent value="user-permissions" className="mt-4">
          <UserPermissionsQueryView />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 图标导入（用于Tabs显示）
import { FileText, Eye } from "lucide-react";
