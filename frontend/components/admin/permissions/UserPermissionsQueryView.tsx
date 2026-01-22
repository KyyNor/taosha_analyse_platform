"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { loginRecordApi, permissionApi } from "@/lib/api";
import { Eye, User, Building2, Shield as ShieldIcon, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface LoginRecord {
  user_id: string;
  user_name: string;
  branch_no: string;
  branch_name: string;
  role_id_list: string[];
  role_name_list: string[];
  last_login_time: string;
}

interface PermissionTreeNode {
  id: string;
  path: string;
  name: string;
  description?: string;
  level: number;
  children: PermissionTreeNode[];
}

export default function UserPermissionsQueryView() {
  const [loginRecords, setLoginRecords] = useState<LoginRecord[]>([]);
  const [selectedUser, setSelectedUser] = useState<LoginRecord | null>(null);
  const [permissions, setPermissions] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadLoginRecords();
  }, []);

  const loadLoginRecords = async () => {
    try {
      setLoading(true);
      const response = await loginRecordApi.getLoginRecords();
      setLoginRecords(response.login_records || []);
    } catch (err) {
      toast.error("加载登录记录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleUserSelect = async (userId: string) => {
    const user = loginRecords.find((u) => u.user_id === userId);
    if (user) {
      setSelectedUser(user);
      loadUserPermissions(userId);
    }
  };

  const loadUserPermissions = async (userId: string) => {
    try {
      setLoading(true);
      const response = await permissionApi.getUserEffectivePermissions(userId);
      setPermissions(response);
    } catch (err) {
      toast.error("加载用户权限失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 用户选择器 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">选择用户</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selectedUser?.user_id || ""} onValueChange={handleUserSelect}>
            <SelectTrigger>
              <SelectValue placeholder="请选择已登录过的用户" />
            </SelectTrigger>
            <SelectContent>
              {loginRecords.map((record) => (
                <SelectItem key={record.user_id} value={record.user_id}>
                  <div className="flex flex-col">
                    <span className="font-medium">{record.user_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {record.user_id} - {record.branch_name}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* 权限详情 */}
      {selectedUser && permissions && (
        <>
          {/* 用户信息卡片 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-5 w-5" />
                  用户信息
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-sm text-muted-foreground">用户ID</label>
                  <p className="font-medium">{selectedUser.user_id}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">用户名</label>
                  <p className="font-medium">{selectedUser.user_name}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    所属部门
                  </label>
                  <p className="font-medium">{selectedUser.branch_name}</p>
                  <p className="text-xs text-muted-foreground">{selectedUser.branch_no}</p>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground flex items-center gap-2">
                    <ShieldIcon className="h-4 w-4" />
                    拥有角色
                  </label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedUser.role_name_list.map((role, index) => (
                      <Badge key={index} variant="secondary">
                        {role}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">最后登录</label>
                  <p className="text-sm">
                    {new Date(selectedUser.last_login_time).toLocaleString("zh-CN")}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* 权限统计卡片 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  权限统计
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground">总权限数</label>
                  <p className="text-2xl font-semibold">{permissions.total_permissions}</p>
                </div>
                <Separator />
                <div>
                  <label className="text-sm text-muted-foreground">权限来源</label>
                  <div className="space-y-2 mt-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">来自部门</span>
                      <Badge variant="outline">
                        {selectedUser.branch_name}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">来自角色</span>
                      <div className="flex gap-1">
                        {selectedUser.role_name_list.map((role, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 层级化权限树 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                最终权限列表
                <Badge className="ml-2">{permissions.total_permissions}</Badge>
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                用户 {selectedUser.user_name} 可访问的所有页面
              </p>
            </CardHeader>
            <CardContent>
              {permissions.permissions_tree && permissions.permissions_tree.length > 0 ? (
                <PermissionTreeNodeView nodes={permissions.permissions_tree} />
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  该用户暂无任何页面权限
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// 权限树节点组件
interface PermissionTreeNodeViewProps {
  nodes: PermissionTreeNode[];
  level?: number;
}

function PermissionTreeNodeView({ nodes, level = 0 }: PermissionTreeNodeViewProps) {
  return (
    <div className="space-y-2">
      {nodes.map((node) => (
        <div key={node.id}>
          <div
            className="flex items-center gap-2 p-3 rounded border bg-card hover:bg-muted/50 transition-colors"
            style={{ marginLeft: `${level * 24}px` }}
          >
            {node.children && node.children.length > 0 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{node.name}</span>
                <Badge variant="outline" className="text-xs">
                  L{node.level}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground font-mono">{node.path}</p>
              {node.description && (
                <p className="text-xs text-muted-foreground mt-1">{node.description}</p>
              )}
            </div>
            <Badge variant="default" className="text-xs">
              ✓ 有权限
            </Badge>
          </div>
          {node.children && node.children.length > 0 && (
            <PermissionTreeNodeView nodes={node.children} level={level + 1} />
          )}
        </div>
      ))}
    </div>
  );
}
