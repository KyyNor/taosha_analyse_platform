"use client";

import { useEffect, useState } from "react";
import { useRequireAdmin } from "@/hooks/useAuth";
import { permissionApi, entityApi, ApiError } from "@/lib/api";
import { Shield, Users, FileText, Copy, Save, Eye } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
}

export default function PermissionsPage() {
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin();

  const [entities, setEntities] = useState<Entity[]>([]);
  const [pages, setPages] = useState<Page[]>([]);
  const [matrix, setMatrix] = useState<Record<string, Record<string, boolean>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 过滤状态
  const [entityFilter, setEntityFilter] = useState("");
  const [pageFilter, setPageFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "department" | "role">("all");

  // 复制权限对话框
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [copySource, setCopySource] = useState<string>("");
  const [copyTarget, setCopyTarget] = useState<string>("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [entitiesResponse, pagesResponse, matrixResponse] = await Promise.all([
        entityApi.getEntities(),
        permissionApi.getPages(),
        permissionApi.getPermissionMatrix(),
      ]);

      setEntities(entitiesResponse.entities || []);
      setPages(pagesResponse.pages || []);
      setMatrix(matrixResponse.matrix || {});
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "加载权限数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      loadData();
    }
  }, [isAuthenticated, isAdmin]);

  // 过滤实体
  const filteredEntities = entities.filter((entity) => {
    const matchesName =
      entity.name.toLowerCase().includes(entityFilter.toLowerCase()) ||
      entity.code.toLowerCase().includes(entityFilter.toLowerCase());
    const matchesType = typeFilter === "all" || entity.type === typeFilter;
    return matchesName && matchesType;
  });

  // 过滤页面
  const filteredPages = pages.filter(
    (page) =>
      page.name.toLowerCase().includes(pageFilter.toLowerCase()) ||
      page.path.toLowerCase().includes(pageFilter.toLowerCase())
  );

  // 切换权限
  const togglePermission = (entityId: string, pageId: string) => {
    setMatrix((prev) => ({
      ...prev,
      [entityId]: {
        ...prev[entityId],
        [pageId]: !prev[entityId]?.[pageId],
      },
    }));
  };

  // 保存权限
  const savePermissions = async () => {
    try {
      setSaving(true);
      // 为每个实体保存权限
      for (const [entityId, pagePermissions] of Object.entries(matrix)) {
        const pageIds = Object.entries(pagePermissions)
          .filter(([_, hasPermission]) => hasPermission)
          .map(([pageId]) => pageId);
        await permissionApi.assignPermissions(entityId, pageIds);
      }
      toast.success("权限保存成功");
      await loadData();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "保存权限失败");
    } finally {
      setSaving(false);
    }
  };

  // 复制权限
  const handleCopyPermissions = async () => {
    if (!copySource || !copyTarget) return;

    try {
      setSaving(true);
      await permissionApi.copyPermissions(copySource, copyTarget);
      toast.success("权限复制成功");
      setCopyDialogOpen(false);
      setCopySource("");
      setCopyTarget("");
      await loadData();
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "复制权限失败");
    } finally {
      setSaving(false);
    }
  };

  // 统计数据
  const totalPermissions = Object.values(matrix).reduce(
    (total, entityPerms) =>
      total + Object.values(entityPerms).filter(Boolean).length,
    0
  );

  const coverageRate =
    entities.length > 0 && pages.length > 0
      ? Math.round((totalPermissions / (entities.length * pages.length)) * 100)
      : 0;

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
          <Shield className="h-6 w-6" />
          权限分配
        </h1>
        <p className="text-muted-foreground">为部门和角色分配页面访问权限</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">总实体数</p>
                <p className="text-2xl font-semibold">{entities.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-green-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">总页面数</p>
                <p className="text-2xl font-semibold">{pages.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">权限总数</p>
                <p className="text-2xl font-semibold">{totalPermissions}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <Eye className="h-8 w-8 text-amber-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-muted-foreground">覆盖率</p>
                <p className="text-2xl font-semibold">{coverageRate}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 操作栏 */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <Input
            placeholder="搜索实体..."
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
            className="w-full sm:w-48"
          />
          <Input
            placeholder="搜索页面..."
            value={pageFilter}
            onChange={(e) => setPageFilter(e.target.value)}
            className="w-full sm:w-48"
          />
          <Select
            value={typeFilter}
            onValueChange={(value: "all" | "department" | "role") =>
              setTypeFilter(value)
            }
          >
            <SelectTrigger className="w-full sm:w-36">
              <SelectValue placeholder="类型筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">所有类型</SelectItem>
              <SelectItem value="department">部门</SelectItem>
              <SelectItem value="role">角色</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setCopyDialogOpen(true)}>
            <Copy className="h-4 w-4 mr-2" />
            复制权限
          </Button>
          <Button variant="outline" onClick={loadData} disabled={loading}>
            刷新
          </Button>
          <Button onClick={savePermissions} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "保存中..." : "保存更改"}
          </Button>
        </div>
      </div>

      {/* 权限矩阵 */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground">
            加载权限矩阵中...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky left-0 bg-card z-10 min-w-[200px]">
                    实体
                  </TableHead>
                  {filteredPages.map((page) => (
                    <TableHead
                      key={page.id}
                      className="text-center min-w-[120px]"
                      title={page.path}
                    >
                      <div className="truncate">{page.name}</div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEntities.map((entity) => (
                  <TableRow key={entity.id}>
                    <TableCell className="sticky left-0 bg-card z-10 border-r">
                      <div className="flex items-center gap-2">
                        {entity.type === "department" ? (
                          <Users className="h-4 w-4 text-blue-500" />
                        ) : (
                          <Shield className="h-4 w-4 text-green-500" />
                        )}
                        <div>
                          <div className="font-medium">{entity.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {entity.code}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    {filteredPages.map((page) => (
                      <TableCell key={page.id} className="text-center">
                        <Checkbox
                          checked={matrix[entity.id]?.[page.id] || false}
                          onCheckedChange={() =>
                            togglePermission(entity.id, page.id)
                          }
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {filteredEntities.length === 0 && (
              <div className="p-8 text-center">
                <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">没有找到匹配的实体</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 复制权限对话框 */}
      <Dialog open={copyDialogOpen} onOpenChange={setCopyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>复制权限</DialogTitle>
            <DialogDescription>
              将一个实体的权限复制到另一个实体
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>源实体（复制自）</Label>
              <Select value={copySource} onValueChange={setCopySource}>
                <SelectTrigger>
                  <SelectValue placeholder="请选择源实体" />
                </SelectTrigger>
                <SelectContent>
                  {entities.map((entity) => (
                    <SelectItem key={entity.id} value={entity.id}>
                      {entity.name} ({entity.type === "department" ? "部门" : "角色"})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>目标实体（复制到）</Label>
              <Select value={copyTarget} onValueChange={setCopyTarget}>
                <SelectTrigger>
                  <SelectValue placeholder="请选择目标实体" />
                </SelectTrigger>
                <SelectContent>
                  {entities
                    .filter((entity) => entity.id !== copySource)
                    .map((entity) => (
                      <SelectItem key={entity.id} value={entity.id}>
                        {entity.name} ({entity.type === "department" ? "部门" : "角色"})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            {copySource && copyTarget && (
              <Alert>
                <AlertDescription>
                  将复制{" "}
                  <strong>
                    {entities.find((e) => e.id === copySource)?.name}
                  </strong>{" "}
                  的所有权限到{" "}
                  <strong>
                    {entities.find((e) => e.id === copyTarget)?.name}
                  </strong>
                  。目标实体的现有权限将被覆盖。
                </AlertDescription>
              </Alert>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCopyDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleCopyPermissions}
              disabled={!copySource || !copyTarget || saving}
            >
              {saving ? "复制中..." : "确认复制"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
