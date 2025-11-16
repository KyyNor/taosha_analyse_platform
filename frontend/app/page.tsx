'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CopilotChat } from "@copilotkit/react-ui";
import { Bot } from "lucide-react";
import Layout from "@/components/layout/Layout";

export default function Home() {
  return (
    <Layout>
      {/* 页面头部 */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          淘沙分析平台
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          基于AI的自然语言转SQL分析平台，让数据分析变得简单高效
        </p>
      </div>

      {/* AI助手区域 */}
      <Card className="max-w-4xl mx-auto">
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
          <div className="h-96">
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
    </Layout>
  );
}

