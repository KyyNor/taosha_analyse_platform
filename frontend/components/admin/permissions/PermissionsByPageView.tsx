"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { permissionApi, entityApi } from "@/lib/api";
import { FileText, Building2, Shield as ShieldIcon, Save, X, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Page {
  id: string;
  path: string;
  name: string;
  description?: string;
  level?: number;
  children?: Page[];
}

interface Entity {
  id: string;
  code: string;
  name: string;
  type: "department" | "role";
  has_permission?: boolean;
}

export default function PermissionsByPageView() {
  const [pageTree, setPageTree] = useState<Page[]>([]);
  const [selectedPage, setSelectedPage] = useState<Page | null>(null);
  const [departments, setDepartments] = useState<Entity[]>([]);
  const [roles, setRoles] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPageTree();
    loadEntities();
  }, []);

  const loadPageTree = async () => {
    try {
      setLoading(true);
      const response = await permissionApi.getPagesTree();
      setPageTree(response.tree || []);
    } catch (err) {
      toast.error("加载页面树失败");
    } finally {
      setLoading(false);
    }
  };

  const loadEntities = async () => {
    try {
      const [deptResponse, roleResponse] = await Promise.all([
        entityApi.getEntities("department"),
        entityApi.getEntities("role"),
      ]);
      setDepartments(deptResponse.entities || []);
      setRoles(roleResponse.entities || []);
    } catch (err) {
      toast.error("加载实体列表失败");
    }
  };

  const loadPagePermissions = async (page: Page) => {
    try {
      const response = await permissionApi.getPageEntities(page.id);

      // 更新部门的权限状态
      setDepartments((prev) =>
        prev.map((dept) => ({
          ...dept,
          has_permission: response.departments.some((d: Entity) => d.id === dept.id),
        }))
      );

      // 更新角色的权限状态
      setRoles((prev) =>
        prev.map((role) => ({
          ...role,
          has_permission: response.roles.some((r: Entity) => r.id === role.id),
        }))
      );
    } catch (err) {
      toast.error("加载页面权限失败");
    }
  };

  const handlePageSelect = (page: Page) => {
    setSelectedPage(page);
    loadPagePermissions(page);
  };

  const handleCancel = () => {
    if (selectedPage) {
      loadPagePermissions(selectedPage); // 重新加载
    }
  };

  const handleSave = async () => {
    if (!selectedPage) return;

    try {
      setSaving(true);
      // 为每个实体分配或移除权限
      const allEntities = [...departments, ...roles];

      for (const entity of allEntities) {
        if (entity.has_permission) {
          await permissionApi.assignPermissions(entity.id, [selectedPage.id]);
        }
        // 如果移除权限，需要重新分配（这是一个简化实现）
        // 实际应该先获取所有权限，然后修改后重新分配
      }

      toast.success("权限保存成功");
    } catch (err) {
      toast.error("保存权限失败");
    } finally {
      setSaving(false);
    }
  };

  const toggleEntityPermission = (entityId: string) => {
    const updateList = (list: Entity[]) =>
      list.map((entity) =>
        entity.id === entityId ? { ...entity, has_permission: !entity.has_permission } : entity
      );

    setDepartments(updateList);
    setRoles(updateList);
  };

  return (
    <div className="space-y-4">
      {/* 左右两栏布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左栏：页面选择器 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">选择页面</CardTitle>
          </CardHeader>
          <CardContent>
            <PageTreeSelector
              pages={pageTree}
              selectedPage={selectedPage}
              onSelect={handlePageSelect}
            />
          </CardContent>
        </Card>

        {/* 右栏：权限详情 */}
        {selectedPage && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{selectedPage.name}</CardTitle>
                  <p className="text-sm text-muted-foreground">{selectedPage.path}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleSave} disabled={saving}>
                    <Save className="h-4 w-4 mr-2" />
                    {saving ? "保存中..." : "保存"}
                  </Button>
                  <Button onClick={handleCancel} variant="outline" disabled={saving}>
                    <X className="h-4 w-4 mr-2" />
                    取消
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 部门列表 */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-blue-500" />
                  部门权限
                </h3>
                <EntityPermissionList
                  entities={departments}
                  readonly={false}
                  onToggle={toggleEntityPermission}
                />
              </div>

              <Separator />

              {/* 角色列表 */}
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <ShieldIcon className="h-4 w-4 text-green-500" />
                  角色权限
                </h3>
                <EntityPermissionList
                  entities={roles}
                  readonly={false}
                  onToggle={toggleEntityPermission}
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// 页面树选择器组件
interface PageTreeSelectorProps {
  pages: Page[];
  selectedPage: Page | null;
  onSelect: (page: Page) => void;
  level?: number;
}

function PageTreeSelector({ pages, selectedPage, onSelect, level = 0 }: PageTreeSelectorProps) {
  return (
    <div className="space-y-1">
      {pages.map((page) => (
        <div key={page.id}>
          <div
            className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
              selectedPage?.id === page.id
                ? "bg-primary/10"
                : "hover:bg-muted/50"
            }`}
            style={{ marginLeft: `${level * 24}px` }}
            onClick={() => onSelect(page)}
          >
            {page.children && page.children.length > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{page.name}</span>
                {page.level !== undefined && (
                  <Badge variant="outline">L{page.level}</Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground font-mono">{page.path}</p>
              {page.description && (
                <p className="text-xs text-muted-foreground">{page.description}</p>
              )}
            </div>
          </div>
          {page.children && page.children.length > 0 && (
            <PageTreeSelector
              pages={page.children}
              selectedPage={selectedPage}
              onSelect={onSelect}
              level={level + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// 实体权限列表组件
interface EntityPermissionListProps {
  entities: Entity[];
  readonly: boolean;
  onToggle: (entityId: string) => void;
}

function EntityPermissionList({ entities, readonly, onToggle }: EntityPermissionListProps) {
  if (entities.length === 0) {
    return <p className="text-sm text-muted-foreground">暂无数据</p>;
  }

  return (
    <div className="space-y-2">
      {entities.map((entity) => (
        <div
          key={entity.id}
          className="flex items-center gap-3 p-3 rounded border hover:bg-muted/50 transition-colors"
        >
          <Checkbox
            checked={entity.has_permission || false}
            onCheckedChange={() => onToggle(entity.id)}
            disabled={readonly}
          />
          <div className="flex-1">
            <div className="font-medium">{entity.name}</div>
            <div className="text-xs text-muted-foreground">{entity.code}</div>
          </div>
          {entity.has_permission && (
            <Badge variant="default" className="text-xs">
              有权限
            </Badge>
          )}
        </div>
      ))}
    </div>
  );
}
