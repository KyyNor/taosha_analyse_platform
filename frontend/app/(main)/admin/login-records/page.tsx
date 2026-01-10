"use client";

import { useEffect, useState } from "react";
import { useRequireAdmin } from "@/hooks/useAuth";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { loginRecordApi, ApiError } from "@/lib/api";
import { Clock, Users, UserCheck, TrendingUp, Calendar } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface LoginRecord {
  user_id: string;
  user_name: string;
  branch_no: string;
  branch_name: string;
  role_id_list: string[];
  role_name_list: string[];
  last_login_time: string;
  created_at: string;
  updated_at: string;
}

interface LoginSummary {
  total_users: number;
  active_users_today: number;
  active_users_week: number;
  active_users_month: number;
  latest_login_time?: string;
  most_active_department?: string;
  most_active_role?: string;
}

export default function LoginRecordsPage() {
  const { isAuthenticated, isLoading: authLoading, isAdmin } = useRequireAdmin();

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<LoginRecord[]>([]);
  const [summary, setSummary] = useState<LoginSummary | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };
      if (searchQuery.trim()) {
        params.user_id = searchQuery.trim();
      }

      const response = await loginRecordApi.getLoginRecords(params);
      setData(response.records || []);
      setTotal(response.total || 0);
    } catch (err) {
      const error = err as ApiError;
      toast.error(error.message || "加载登录记录失败");
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const summaryData = await loginRecordApi.getLoginSummary();
      setSummary(summaryData);
    } catch (err) {
      console.error("加载统计信息失败:", err);
    }
  };

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      load();
      loadSummary();
    }
  }, [isAuthenticated, isAdmin]);

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      load();
    }
  }, [currentPage, searchQuery]);

  // 搜索变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // 渲染角色标签
  const renderRoleBadges = (roleNames: string[]) => {
    if (!roleNames || roleNames.length === 0) {
      return <span className="text-muted-foreground">无角色</span>;
    }
    return (
      <div className="flex flex-wrap gap-1">
        {roleNames.map((roleName, index) => (
          <Badge key={index} variant="secondary">
            {roleName}
          </Badge>
        ))}
      </div>
    );
  };

  // 表格列配置
  const columns = [
    { key: "user_id", label: "用户ID", type: "text" as const },
    { key: "user_name", label: "用户名", type: "text" as const },
    { key: "branch_name", label: "部门", type: "text" as const },
    {
      key: "role_name_list",
      label: "角色",
      type: "custom" as const,
      render: (value: string[]) => renderRoleBadges(value),
    },
    { key: "last_login_time", label: "最后登录", type: "datetime" as const },
    { key: "created_at", label: "首次记录", type: "datetime" as const },
  ];

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
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
          <Clock className="h-6 w-6" />
          登录记录
        </h1>
        <p className="text-muted-foreground">查看用户登录历史和活跃度统计</p>
      </div>

      {/* 统计卡片 */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center">
                <Users className="h-8 w-8 text-blue-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    总用户数
                  </p>
                  <p className="text-2xl font-semibold">{summary.total_users}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center">
                <UserCheck className="h-8 w-8 text-green-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    今日活跃
                  </p>
                  <p className="text-2xl font-semibold">
                    {summary.active_users_today}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center">
                <TrendingUp className="h-8 w-8 text-purple-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    本周活跃
                  </p>
                  <p className="text-2xl font-semibold">
                    {summary.active_users_week}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center">
                <Calendar className="h-8 w-8 text-amber-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    本月活跃
                  </p>
                  <p className="text-2xl font-semibold">
                    {summary.active_users_month}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        searchPlaceholder="搜索用户ID..."
        emptyText="暂无登录记录"
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        showActions={false}
        pagination={{
          pageSize,
          currentPage,
          total,
          onPageChange: handlePageChange,
        }}
      />

      {/* 额外信息 */}
      {summary && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardContent className="pt-6">
              <h3 className="text-lg font-semibold mb-4">系统活跃度</h3>
              <div className="space-y-3">
                {summary.latest_login_time && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      最新登录时间:
                    </span>
                    <span className="text-sm font-medium">
                      {new Date(summary.latest_login_time).toLocaleString("zh-CN")}
                    </span>
                  </div>
                )}
                {summary.most_active_department && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      最活跃部门:
                    </span>
                    <span className="text-sm font-medium">
                      {summary.most_active_department}
                    </span>
                  </div>
                )}
                {summary.most_active_role && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      最活跃角色:
                    </span>
                    <span className="text-sm font-medium">
                      {summary.most_active_role}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <h3 className="text-lg font-semibold mb-4">使用说明</h3>
              <div className="text-sm text-muted-foreground space-y-2">
                <p>• 登录记录显示用户最后一次登录的信息</p>
                <p>• 可以按用户ID进行搜索</p>
                <p>• 角色信息显示用户当前拥有的所有角色</p>
                <p>• 统计数据每次页面加载时更新</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
