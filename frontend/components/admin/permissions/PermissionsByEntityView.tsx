"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { permissionApi, entityApi } from "@/lib/api";
import { Shield, Users, Edit, Save, X, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/select";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Entity {
  id: string;
  code: string;
  name: string;
  type: "department" | "role";
}

interface Page {
  id: string;
  path: string;
  name: string;
  description?: string;
  level?: number;
  children?: Page[];
}

export default function PermissionsByEntityView() {
  // 状态管理
  const [entityType, setEntityType] = useState<"department" | "role">("department");
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [pageTree, setPageTree] = useState<Page[]>([]);
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 加载实体列表
  useEffect(() => {
    loadEntities();
  }, [entityType]);

  // 加载页面树
  useEffect(() => {
    loadPageTree();
  }, []);

  // 加载实体权限
  useEffect(() => {
    if (selectedEntity && mode === "view") {
      loadEntityPermissions();
    }
  }, [selectedEntity]);

  const loadEntities = async () => {
    try {
      setLoading(true);
      const response = await entityApi.getEntities(entityType);
      setEntities(response.entities || []);
    } catch (err) {
      toast.error("加载实体列表失败");
    } finally {
      setLoading(false);
    }
  };

  const loadPageTree = async () => {
    try {
      const response = await permissionApi.getPagesTree();
      setPageTree(response.tree || []);
    } catch (err) {
      toast.error("加载页面树失败");
    }
  };

  const loadEntityPermissions = async () => {
    if (!selectedEntity) return;

    try {
      const response = await permissionApi.getEntityPermissions(selectedEntity.id);
      const pageIds = new Set(response.pages.map((p: Page) => p.id));
      setPermissions(pageIds);
    } catch (err) {
      toast.error("加载权限失败");
    }
  };

  const handleEdit = () => {
    setMode("edit");
  };

  const handleCancel = () => {
    setMode("view");
    loadEntityPermissions(); // 重新加载原始权限
  };

  const handleSave = async () => {
    if (!selectedEntity) return;

    try {
      setSaving(true);
      await permissionApi.assignPermissions(selectedEntity.id, Array.from(permissions));
      toast.success("权限保存成功");
      setMode("view");
    } catch (err) {
      toast.error("保存权限失败");
    } finally {
      setSaving(false);
    }
  };

  const togglePermission = (pageId: string) => {
    setPermissions((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(pageId)) {
        newSet.delete(pageId);
      } else {
        newSet.add(pageId);
      }
      return newSet;
    });
  };

  return (
    <div className="space-y-4">
      {/* 实体类型选择 */}
      <div className="flex gap-2">
        <Button
          variant={entityType === "department" ? "default" : "outline"}
          onClick={() => {
            setEntityType("department");
            setSelectedEntity(null);
          }}
        >
          <Users className="h-4 w-4 mr-2" />
          部门权限
        </Button>
        <Button
          variant={entityType === "role" ? "default" : "outline"}
          onClick={() => {
            setEntityType("role");
            setSelectedEntity(null);
          }}
        >
          <Shield className="h-4 w-4 mr-2" />
          角色权限
        </Button>
      </div>

      {/* 实体选择器 */}
      {entities.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">选择{entityType === "department" ? "部门" : "角色"}</CardTitle>
          </CardHeader>
          <CardContent>
            <Select
              value={selectedEntity?.id || ""}
              onValueChange={(value) => {
                const entity = entities.find((e) => e.id === value);
                if (entity) {
                  setSelectedEntity(entity);
                  setPermissions(new Set());
                  setMode("view");
                }
              }}
              disabled={mode === "edit"}
            >
              <SelectTrigger>
                <SelectValue placeholder={`请选择${entityType === "department" ? "部门" : "角色"}`} />
              </SelectTrigger>
              <SelectContent>
                {entities.map((entity) => (
                  <SelectItem key={entity.id} value={entity.id}>
                    {entity.name} ({entity.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      {/* 权限配置区域 */}
      {selectedEntity && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">
                {selectedEntity.name} 的页面权限
              </CardTitle>
              {mode === "view" ? (
                <Button onClick={handleEdit} variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  修改
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button onClick={handleSave} disabled={saving}>
                    <Save className="h-4 w-4 mr-2" />
                    {saving ? "保存中..." : "保存"}
                  </Button>
                  <Button onClick={handleCancel} variant="outline">
                    <X className="h-4 w-4 mr-2" />
                    取消
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {mode === "view" ? (
              <PageTreeView
                pages={pageTree}
                permissions={permissions}
                readonly
              />
            ) : (
              <PageTreeView
                pages={pageTree}
                permissions={permissions}
                onToggle={togglePermission}
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// 页面树组件
interface PageTreeViewProps {
  pages: Page[];
  permissions: Set<string>;
  readonly?: boolean;
  onToggle?: (pageId: string) => void;
  level?: number;
}

function PageTreeView({ pages, permissions, readonly, onToggle, level = 0 }: PageTreeViewProps) {
  return (
    <div className="space-y-2">
      {pages.map((page) => (
        <div key={page.id}>
          <div
            className="flex items-center gap-2 p-2 hover:bg-muted/50 rounded"
            style={{ marginLeft: `${level * 24}px` }}
          >
            {page.children && page.children.length > 0 && (
              <TreeNodeIcon level={page.level || 0} />
            )}
            <Checkbox
              checked={permissions.has(page.id)}
              onCheckedChange={() => onToggle?.(page.id)}
              disabled={readonly}
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{page.name}</span>
                {page.level !== undefined && (
                  <Badge variant="outline">L{page.level}</Badge>
                )}
              </div>
              {page.description && (
                <p className="text-xs text-muted-foreground">{page.description}</p>
              )}
            </div>
          </div>
          {page.children && page.children.length > 0 && (
            <PageTreeView
              pages={page.children}
              permissions={permissions}
              readonly={readonly}
              onToggle={onToggle}
              level={level + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function TreeNodeIcon({ level }: { level: number }) {
  return <ChevronRight className="h-4 w-4 text-muted-foreground" />;
}
