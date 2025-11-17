"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";

type Props = {
  initialQuery?: string;
  onSubmit?: (payload: { text: string }) => void;
  onCancel?: () => void;
};

export default function QueryForm({ initialQuery = "", onSubmit, onCancel }: Props) {
  const [text, setText] = useState(initialQuery);
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (initialQuery) {
      setText(initialQuery);
      ref.current?.focus();
      ref.current?.select();
    }
  }, [initialQuery]);

  return (
    <div className="space-y-3">
      <Textarea
        ref={ref}
        placeholder="使用自然语言描述您的查询需求..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="flex gap-2">
        <Button onClick={() => text.trim() && onSubmit?.({ text })}>提交查询</Button>
        <Button variant="outline" onClick={() => onCancel?.()}>取消</Button>
      </div>
    </div>
  );
}