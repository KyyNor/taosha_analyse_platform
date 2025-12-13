import "../styles/globals.css";
import { ReactNode } from "react";
import { AppProvider } from "../lib/state/app";
import { ThemeProvider } from "../lib/state/theme";
import { Toaster } from "../components/ui/sonner";
import { TooltipProvider } from "../components/ui/tooltip";

export const metadata = {
  title: "淘沙数据分析平台",
  description: "淘沙数据分析平台"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-dvh bg-background text-foreground">
        <ThemeProvider>
          <AppProvider>
            <TooltipProvider>
              {children}
            </TooltipProvider>
            <Toaster richColors closeButton />
          </AppProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}