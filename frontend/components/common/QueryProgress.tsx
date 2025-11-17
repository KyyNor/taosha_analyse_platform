"use client";
import { Button } from "../ui/button";

type Props = {
  onCancel?: () => void;
  onCopySQL?: (sql: string) => void;
  sql?: string;
};

export default function QueryProgress({ onCancel, onCopySQL, sql }: Props) {
  return (
    <div className="flex items-center justify-between rounded-md border p-3">
      <div className="text-sm">查询进行中...</div>
      <div className="flex gap-2">
        {sql ? (
          <Button variant="outline" onClick={() => onCopySQL?.(sql!)}>复制 SQL</Button>
        ) : null}
        <Button variant="secondary" onClick={() => onCancel?.()}>取消</Button>
      </div>
    </div>
  );
}