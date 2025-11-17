import "../styles/globals.css";
import { ReactNode } from "react";
import { AppProvider } from "../lib/state/app";
import { ThemeProvider } from "../lib/state/theme";

export const metadata = {
  title: "Taosha Analyse Platform",
  description: "Frontend migrated to Next.js"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-dvh bg-background text-foreground">
        <ThemeProvider>
          <AppProvider>{children}</AppProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}