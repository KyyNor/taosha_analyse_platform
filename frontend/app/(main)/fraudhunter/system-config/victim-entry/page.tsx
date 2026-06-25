"use client";
import { useEffect, useState, useRef } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import {
  getVictimEntries,
  updateVictimEntry,
  VictimEntryRecord,
} from "@/lib/services/metadataService";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const ACCOUNT_NO_MAX_LEN = 50;
const ACCOUNT_NAME_MAX_LEN = 256;

export default function Page() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);

  // 分页
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 搜索（受控，与 MetadataTable 配合）
  const [searchQuery, setSearchQuery] = useState("");

  // 编辑/新增弹窗
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [recordToEdit, setRecordToEdit] = useState<string | null>(null); // null = 新增
  const [form, setForm] = useState<VictimEntryRecord>({
    account_no: "",
    account_name: "",
  });
  const [saving, setSaving] = useState(false);

  // 导入弹窗
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getVictimEntries({
        page: currentPage,
        page_size: pageSize,
        search: searchQuery || undefined,
      });
      setData(res?.items ?? []);
      setTotal(res?.total ?? 0);
    } catch {
      toast.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [currentPage, searchQuery]);

  const handlePageChange = (page: number) => {
    // 删除末页最后一条后自动回到上一页，防止白屏
    if (data.length === 1 && page < currentPage) {
      setCurrentPage(Math.max(1, page));
    } else {
      setCurrentPage(page);
    }
  };

  const handleEdit = (item: any) => {
    setRecordToEdit(item.account_no);
    setForm({
      account_no: item.account_no ?? "",
      account_name: item.account_name ?? "",
    });
    setEditDialogOpen(true);
  };

  const handleAdd = () => {
    setRecordToEdit(null);
    setForm({ account_no: "", account_name: "" });
    setEditDialogOpen(true);
  };

  const validateForm = (): boolean => {
    const trimmedAccountNo = form.account_no?.trim() ?? "";

    if (!trimmedAccountNo) {
      toast.error("账号不能为空");
      return false;
    }

    if (trimmedAccountNo.length > ACCOUNT_NO_MAX_LEN) {
      toast.error(`账号长度不能超过 ${ACCOUNT_NO_MAX_LEN} 个字符`);
      return false;
    }

    if ((form.account_name?.trim() ?? "").length > ACCOUNT_NAME_MAX_LEN) {
      toast.error(`户名长度不能超过 ${ACCOUNT_NAME_MAX_LEN} 个字符`);
      return false;
    }

    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    const trimmedAccountNo = form.account_no!.trim();

    setSaving(true);
    try {
      if (recordToEdit === null) {
        await updateVictimEntry(
          { ...form, account_no: trimmedAccountNo },
          "POST"
        );
        toast.success("新增成功");
      } else {
        await updateVictimEntry(
          { ...form, account_no: trimmedAccountNo },
          "PUT",
          recordToEdit
        );
        toast.success("更新成功");
      }
      setEditDialogOpen(false);
      load();
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ??
        e?.message ??
        "保存失败，请重试";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (item: any) => {
    try {
      await updateVictimEntry({}, "DELETE", item.account_no);
      toast.success("删除成功");
      load();
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ??
        e?.message ??
        "删除失败，请重试";
      toast.error(msg);
    }
  };

  // ---------- 导入相关 ----------
  const openImportDialog = () => {
    setSelectedFile(null);
    setImportDialogOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
        toast.error("仅支持 Excel 文件格式（.xlsx/.xls）");
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleImportConfirm = async () => {
    if (!selectedFile) {
      toast.error("请选择要导入的文件");
      return;
    }

    setImporting(true);
    try {
      // 直接把文件发给后端，由后端解析和处理
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await fetch("/api/taosha/v1/fraudhunter/system-config/victim-entries/import", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      if (res.ok && result.success) {
        toast.success(result.message);
        setImportDialogOpen(false);
        load(); // 刷新列表
      } else {
        toast.error(result.detail || result.message || "导入失败");
      }
    } catch (e: any) {
      toast.error(e?.message ?? "导入失败，请检查网络连接");
    } finally {
      setImporting(false);
    }
  };

  const columns = [
    { key: "account_no", label: "账号", type: "text" as const, maxLength: 30 },
    { key: "account_name", label: "户名", type: "text" as const },
  ];

  return (
    <div className="container mx-auto py-6 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">受害人录入维护</h1>
        <Button variant="outline" onClick={openImportDialog}>
          导入
        </Button>
      </div>

      <Card className="p-4">
        <MetadataTable
          data={data}
          columns={columns}
          loading={loading}
          onRefresh={load}
          onAdd={handleAdd}
          onEdit={handleEdit}
          onDelete={handleDelete}
          searchPlaceholder="搜索账号、户名..."
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          pagination={{
            pageSize,
            currentPage,
            total,
            onPageChange: handlePageChange,
          }}
        />
      </Card>

      {/* 编辑/新增弹窗 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {recordToEdit === null ? "新增受害人" : "编辑受害人"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">
                账号&nbsp;<span className="text-destructive">*</span>
              </Label>
              <Input
                className="col-span-3"
                value={form.account_no ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, account_no: e.target.value }))
                }
                placeholder="输入账号"
                disabled={recordToEdit !== null}
                maxLength={ACCOUNT_NO_MAX_LEN + 1}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">户名</Label>
              <Input
                className="col-span-3"
                value={form.account_name ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, account_name: e.target.value }))
                }
                placeholder="输入户名"
                maxLength={ACCOUNT_NAME_MAX_LEN + 1}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 导入弹窗 */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>导入受害人数据</DialogTitle>
          </DialogHeader>

          <div className="py-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              请上传 Excel 文件，第一行应为表头，包含&quot;账号&quot;和&quot;户名&quot;两列。<br/>
              已存在的账号将被覆盖，无则为新增。
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              className="w-full"
            >
              选择文件
            </Button>
            {selectedFile && (
              <p className="text-sm text-green-600">
                已选择: {selectedFile.name}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleImportConfirm} disabled={!selectedFile || importing}>
              {importing ? "导入中..." : "确定导入"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}