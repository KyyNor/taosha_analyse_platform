"use client";

import { useEffect, useState } from "react";
import { useRequireAdmin } from "@/hooks/useAuth";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { entityApi, ApiError } from "@/lib/api";
import { Building } from "lucide-react";
import { toast } from "sonner";
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
import { Switch } from "@/components/ui/switch";

interface Department {
  id: string;
  code: string;
  name: string;
  type: "department";
  description?: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

interface DepartmentFormData {
  code: string;
  name: string;
  description: string;
  is_admin: boolean;
}

export default function DepartmentsPage() {
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin();

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Department[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // 模态框状态
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Department | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState<DepartmentFormData>({
    code: "",
    name: "",
    description: "",
    is_admin: false,
  });

  const load = async () => {
    setLoading(true);
    try {
      const response = await entityApi.getEntities("department");
      setData(response.entities || []);
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "加载部门列表失败");
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
    (dept) =>
      dept.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dept.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 表格列配置
  const columns = [
    { key: "code", label: "部门编码", type: "text" as const },
    { key: "name", label: "部门名称", type: "text" as const },
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
          <span className="text-muted-foreground">普通部门</span>
        )
    },
    { key: "description", label: "描述", type: "text" as const, maxLength: 50 },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  const resetForm = () => {
    setFormData({ code: "", name: "", description: "", is_admin: false });
  };

  const handleAdd = () => {
    resetForm();
    setCreateDialogOpen(true);
  };

  const handleEdit = (item: Department) => {
    setSelectedItem(item);
    setFormData({
      code: item.code,
      name: item.name,
      description: item.description || "",
      is_admin: item.is_admin,
    });
    setEditDialogOpen(true);
  };

  const handleDelete = async (item: Department) => {
    try {
      await entityApi.deleteEntity(item.id);
      toast.success("删除成功");
      await load();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "删除失败");
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setFormLoading(true);
      await entityApi.createEntity({
        code: formData.code,
        name: formData.name,
        type: "department",
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
          <Building className="h-6 w-6" />
          部门管理
        </h1>
        <p className="text-muted-foreground">管理系统中的部门信息和权限分配</p>
      </div>

      <MetadataTable
        data={filteredData}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="搜索部门名称或编码..."
        emptyText="暂无部门数据"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* 创建部门对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建部门</DialogTitle>
            <DialogDescription>创建一个新的部门</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="code">部门编码 *</Label>
                <Input
                  id="code"
                  required
                  value={formData.code}
                  onChange={(e) =>
                    setFormData({ ...formData, code: e.target.value })
                  }
                  placeholder="请输入部门编码"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">部门名称 *</Label>
                <Input
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="请输入部门名称"
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
                  placeholder="请输入部门描述"
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="is_admin">管理员部门</Label>
                  <p className="text-xs text-muted-foreground">
                    管理员部门的成员拥有所有页面的访问权限
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

      {/* 编辑部门对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑部门</DialogTitle>
            <DialogDescription>修改部门信息</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEditSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-code">部门编码</Label>
                <Input
                  id="edit-code"
                  value={formData.code}
                  disabled
                  className="bg-muted"
                />
                <p className="text-xs text-muted-foreground">部门编码不可修改</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-name">部门名称 *</Label>
                <Input
                  id="edit-name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="请输入部门名称"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">描述</Label>
                <Textarea
                  id="edit-description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="请输入部门描述"
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="edit-is_admin">管理员部门</Label>
                  <p className="text-xs text-muted-foreground">
                    管理员部门的成员拥有所有页面的访问权限
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
    </div>
  );
}
