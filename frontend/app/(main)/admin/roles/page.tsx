"use client";

import { useEffect, useState } from "react";
import { useRequireAdmin } from "@/hooks/useAuth";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { entityApi, ApiError } from "@/lib/api";
import { Users } from "lucide-react";
import { toast } from "sonner";
import { roleTypeBadgeConfig } from "@/lib/utils/badgeConfigs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Switch } from "@/components/ui/switch";

interface Role {
  id: string;
  code: string;
  name: string;
  type: "role";
  description?: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
  roleType?: string; // 用于显示系统角色/自定义角色
}

interface RoleFormData {
  code: string;
  name: string;
  description: string;
  is_admin: boolean;
}

// 检查是否为系统角色（基于is_admin字段）
const isSystemRole = (role: Role) => {
  return role.is_admin === true;
};

export default function RolesPage() {
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin();

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Role[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // 模态框状态
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Role | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState<RoleFormData>({
    code: "",
    name: "",
    description: "",
    is_admin: false,
  });

  const load = async () => {
    setLoading(true);
    try {
      const response = await entityApi.getEntities("role");
      // 添加 roleType 字段用于显示
      const roles = (response.entities || []).map((role: Role) => ({
        ...role,
        roleType: isSystemRole(role) ? "system" : "custom",
      }));
      setData(roles);
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "加载角色列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      load();
    }
  }, [isAuthenticated, isAdmin]);

  // 过滤数据（前端搜索）
  const filteredData = data.filter(
    (role) =>
      role.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      role.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 表格列配置
  const columns = [
    { key: "code", label: "角色编码", type: "text" as const },
    { key: "name", label: "角色名称", type: "text" as const },
    {
      key: "roleType",
      label: "类型",
      type: "badge" as const,
      badgeConfig: roleTypeBadgeConfig,
    },
    {
      key: "is_admin",
      label: "管理员",
      type: "custom" as const,
      render: (value: boolean) =>
        value ? (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            管理员
          </span>
        ) : (
          <span className="text-muted-foreground">普通角色</span>
        )
    },
    { key: "description", label: "描述", type: "text" as const, maxLength: 50 },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
  ];

  const resetForm = () => {
    setFormData({ code: "", name: "", description: "", is_admin: false });
  };

  const handleAdd = () => {
    resetForm();
    setCreateDialogOpen(true);
  };

  const handleEdit = (item: Role) => {
    setSelectedItem(item);
    setFormData({
      code: item.code,
      name: item.name,
      description: item.description || "",
      is_admin: item.is_admin,
    });
    setEditDialogOpen(true);
  };

  const handleDeleteClick = (item: Role) => {
    if (isSystemRole(item)) {
      toast.error("系统角色不可删除");
      return;
    }
    setSelectedItem(item);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedItem) return;

    try {
      setFormLoading(true);
      await entityApi.deleteEntity(selectedItem.id);
      toast.success("删除成功");
      setDeleteDialogOpen(false);
      setSelectedItem(null);
      await load();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "删除失败");
    } finally {
      setFormLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setFormLoading(true);
      await entityApi.createEntity({
        code: formData.code,
        name: formData.name,
        type: "role",
        description: formData.description || null,
        is_admin: formData.is_admin,
      });
      toast.success("创建成功");
      setCreateDialogOpen(false);
      resetForm();
      await load();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "创建失败");
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    try {
      setFormLoading(true);
      await entityApi.updateEntity(selectedItem.id, {
        name: formData.name,
        description: formData.description || null,
        is_admin: formData.is_admin,
      });
      toast.success("更新成功");
      setEditDialogOpen(false);
      setSelectedItem(null);
      resetForm();
      await load();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "更新失败");
    } finally {
      setFormLoading(false);
    }
  };

  if (authLoading) {
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
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Users className="h-6 w-6" />
          角色管理
        </h1>
        <p className="text-muted-foreground">管理系统中的角色信息和权限分配</p>
      </div>

      <MetadataTable
        data={filteredData}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDeleteClick}
        searchPlaceholder="搜索角色名称或编码..."
        emptyText="暂无角色数据"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* 创建角色对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建角色</DialogTitle>
            <DialogDescription>创建一个新的角色</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="code">角色编码 *</Label>
                <Input
                  id="code"
                  required
                  value={formData.code}
                  onChange={(e) =>
                    setFormData({ ...formData, code: e.target.value })
                  }
                  placeholder="请输入角色编码，如：data_analyst"
                />
                <p className="text-xs text-muted-foreground">
                  建议使用英文或拼音
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">角色名称 *</Label>
                <Input
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="请输入角色名称"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">描述</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="请输入角色描述"
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="is_admin">管理员角色</Label>
                  <p className="text-xs text-muted-foreground">
                    管理员角色拥有所有页面的访问权限
                  </p>
                </div>
                <Switch
                  id="is_admin"
                  checked={formData.is_admin}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_admin: checked })
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateDialogOpen(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={formLoading}>
                {formLoading ? "创建中..." : "创建"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 编辑角色对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑角色</DialogTitle>
            <DialogDescription>修改角色信息</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEditSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-code">角色编码</Label>
                <Input
                  id="edit-code"
                  value={formData.code}
                  disabled
                  className="bg-muted"
                />
                <p className="text-xs text-muted-foreground">角色编码不可修改</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-name">角色名称 *</Label>
                <Input
                  id="edit-name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="请输入角色名称"
                  disabled={selectedItem ? isSystemRole(selectedItem) : false}
                />
                {selectedItem && isSystemRole(selectedItem) && (
                  <p className="text-xs text-amber-600">系统角色名称不可修改</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">描述</Label>
                <Textarea
                  id="edit-description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="请输入角色描述"
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="edit-is_admin">管理员角色</Label>
                  <p className="text-xs text-muted-foreground">
                    管理员角色拥有所有页面的访问权限
                  </p>
                </div>
                <Switch
                  id="edit-is_admin"
                  checked={formData.is_admin}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_admin: checked })
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={formLoading}>
                {formLoading ? "保存中..." : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              您确定要删除角色 <strong>{selectedItem?.name}</strong> 吗？
              删除角色将同时删除该角色的所有权限配置，此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {formLoading ? "删除中..." : "确认删除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
