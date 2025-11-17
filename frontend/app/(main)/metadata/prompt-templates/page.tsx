"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getPromptTemplates } from "@/lib/services/metadataService";
import { useRouter } from "next/navigation";
import { FileText } from "lucide-react";

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const router = useRouter();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getPromptTemplates();
      setData(Array.isArray(res?.data) ? res.data : res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // 表格列配置
  const columns = [
    { key: "template_id", label: "模板ID", type: "number" as const },
    { key: "template_name", label: "模板名称", type: "text" as const },
    { key: "template_description", label: "模板描述", type: "text" as const, maxLength: 60 },
    { key: "template_type", label: "模板类型", type: "text" as const },
    { key: "template", label: "模板内容", type: "text" as const, maxLength: 100 },
    { key: "version", label: "版本", type: "text" as const },
    { key: "is_active", label: "是否启用", type: "boolean" as const },
    { key: "created_at", label: "创建时间", type: "datetime" as const },
    { key: "updated_at", label: "更新时间", type: "datetime" as const },
  ];

  // 操作处理
  const handleView = (item: any, index: number) => {
    router.push(`/metadata/prompt-templates/${item.template_id}`);
  };

  const handleEdit = (item: any, index: number) => {
    router.push(`/metadata/prompt-templates/${item.template_id}?mode=edit`);
  };

  const handleAdd = () => {
    router.push('/metadata/prompt-templates/new');
  };

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          提示词模板管理
        </h1>
        <p className="text-muted-foreground">管理AI查询的提示词模板</p>
      </div>

      <MetadataTable
        data={data}
        columns={columns}
        loading={loading}
        onRefresh={load}
        onAdd={handleAdd}
        onView={handleView}
        onEdit={handleEdit}
        searchPlaceholder="搜索模板名称或描述..."
        emptyText="暂无提示词模板"
      />
    </div>
  );
}