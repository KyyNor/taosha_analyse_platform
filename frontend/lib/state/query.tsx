"use client";
import { createContext, useContext, useMemo, useState } from "react";

type QueryState = {
  text: string;
  setText: (v: string) => void;
};

const Ctx = createContext<QueryState | null>(null);

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [text, setText] = useState("");
  const value = useMemo(() => ({ text, setText }), [text]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useQueryState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useQueryState must be used within QueryProvider");
  return v;
}