"use client";
import { createContext, useContext, useMemo, useState } from "react";

type AgentState = {
  running: boolean;
  setRunning: (v: boolean) => void;
};

const Ctx = createContext<AgentState | null>(null);

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const [running, setRunning] = useState(false);
  const value = useMemo(() => ({ running, setRunning }), [running]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAgentState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAgentState must be used within AgentProvider");
  return v;
}