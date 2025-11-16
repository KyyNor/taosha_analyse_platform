'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CopilotChat } from "@copilotkit/react-ui";
import { Bot } from "lucide-react";
import Layout from "@/components/layout/Layout";

export default function AgentPage() {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        {/* 页面头部 */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold tracking-tight mb-4">
            淘沙Agent
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            智能AI助手，支持自然语言数据查询和分析
          </p>
        </div>

        {/* AI助手区域 */}
        <Card>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Bot className="h-6 w-6 text-indigo-600" />
              <CardTitle>AI智能助手</CardTitle>
            </div>
            <CardDescription>
              有任何关于数据分析的问题？AI助手随时为您服务
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[600px]">
              <CopilotChat
                instructions={"你是淘沙分析平台的AI助手，专门帮助用户进行数据分析和查询。你的职责包括：1. 帮助用户理解数据结构和表关系 2. 协助编写自然语言查询 3. 解释查询结果和数据洞察 4. 提供数据分析建议。请用中文回答，保持专业和友好的语气。"}
                labels={{
                  title: "淘沙AI助手",
                  initial: "👋 您好！我是淘沙数据分析助手，请问有什么可以帮助您的吗？您可以询问任何关于数据查询、分析的问题。",
                }}
                className="h-full"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}