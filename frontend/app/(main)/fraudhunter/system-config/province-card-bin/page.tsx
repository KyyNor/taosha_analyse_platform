"use client";
import { useEffect, useState } from "react";
import { MetadataTable } from "@/components/ui/MetadataTable";
import { getProvinceCardBins, updateProvinceCardBin, ProvinceCardBinRecord } from "@/lib/services/metadataService";
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

const CARD_BIN_MIN_LEN = 4;
const CARD_BIN_MAX_LEN = 20;

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
  const [form, setForm] = useState<ProvinceCardBinRecord>({
    card_bin: "",
    bank_name: "",
    province: "",
    city: "",
  });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getProvinceCardBins({
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
    setRecordToEdit(item.card_bin);
    setForm({
      card_bin: item.card_bin ?? "",
      bank_name: item.bank_name ?? "",
      province: item.province ?? "",
      city: item.city ?? "",
    });
    setEditDialogOpen(true);
  };

  const handleAdd = () => {
    setRecordToEdit(null);
    setForm({ card_bin: "", bank_name: "", province: "", city: "" });
    setEditDialogOpen(true);
  };

  const handleSave = async () => {
    const trimmed = form.card_bin?.trim() ?? "";

    // ── 前端校验：卡BIN非空、纯数字、长度限制 ──────────────────────────
    if (!trimmed) {
      toast.error("卡BIN不能为空");
      return;
    }
    if (!/^\d+$/.test(trimmed)) {
      toast.error("卡BIN必须是纯数字，不能包含字母或符号");
      return;
    }
    if (trimmed.length < CARD_BIN_MIN_LEN || trimmed.length > CARD_BIN_MAX_LEN) {
      toast.error(`卡BIN长度必须在 ${CARD_BIN_MIN_LEN}-${CARD_BIN_MAX_LEN} 位之间`);
      return;
    }

    setSaving(true);
    try {
      if (recordToEdit === null) {
        await updateProvinceCardBin({ ...form, card_bin: trimmed }, "POST");
        toast.success("新增成功");
      } else {
        const keyChanged = trimmed !== recordToEdit;
        await updateProvinceCardBin(
          { ...form, card_bin: trimmed },
          "PUT",
          keyChanged ? recordToEdit : undefined,
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
      await updateProvinceCardBin({}, "DELETE", item.card_bin);
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

  const columns = [
    { key: "card_bin", label: "卡BIN", type: "text" as const, maxLength: 30 },
    { key: "bank_name", label: "银行名称", type: "text" as const },
    { key: "province", label: "省份", type: "text" as const },
    { key: "city", label: "城市", type: "text" as const },
  ];

  return (
    <div className="container mx-auto py-6 space-y-4">
      <h1 className="text-2xl font-bold">省市卡BIN维护</h1>

      <Card className="p-4">
        <MetadataTable
          data={data}
          columns={columns}
          loading={loading}
          onRefresh={load}
          onAdd={handleAdd}
          onEdit={handleEdit}
          onDelete={handleDelete}
          searchPlaceholder="搜索卡BIN、银行、省份、城市..."
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
              {recordToEdit === null ? "新增卡BIN" : "编辑卡BIN"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">
                卡BIN&nbsp;<span className="text-destructive">*</span>
              </Label>
              <Input
                className="col-span-3"
                value={form.card_bin ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, card_bin: e.target.value }))
                }
                placeholder={`${CARD_BIN_MIN_LEN}-${CARD_BIN_MAX_LEN}位数字，如 621098`}
                disabled={recordToEdit !== null}
                maxLength={CARD_BIN_MAX_LEN + 1}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">银行名称</Label>
              <Input
                className="col-span-3"
                value={form.bank_name ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, bank_name: e.target.value }))
                }
                placeholder="如 中国邮政储蓄银行"
                maxLength={256}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">省份</Label>
              <Input
                className="col-span-3"
                value={form.province ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, province: e.target.value }))
                }
                placeholder="如 广东"
                maxLength={256}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right">城市</Label>
              <Input
                className="col-span-3"
                value={form.city ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, city: e.target.value }))
                }
                placeholder="如 深圳"
                maxLength={256}
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
    </div>
  );
}