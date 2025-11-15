import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import { QueryClientProviderWrapper } from "@/components/providers/query-client-provider";
import { Toaster } from "sonner";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "淘沙分析平台",
  description: "基于AI的自然语言转SQL分析平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <QueryClientProviderWrapper>
          <CopilotKit runtimeUrl="/api/copilotkit">
            {children}
            <Toaster />
          </CopilotKit>
        </QueryClientProviderWrapper>
      </body>
    </html>
  );
}
