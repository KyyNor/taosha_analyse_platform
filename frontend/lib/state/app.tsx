"use client";
import { createContext, useContext, useMemo, useState } from "react";

type AppState = {
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
};

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const value = useMemo(() => ({ sidebarOpen, setSidebarOpen }), [sidebarOpen]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState must be used within AppProvider");
  return v;
}