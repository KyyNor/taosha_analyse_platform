import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CopilotChat } from "@copilotkit/react-ui";
import {
  Database,
  BookOpen,
  GitBranch,
  MessageSquare,
  Palette,
  Bot
} from "lucide-react";

const navigationItems = [
  {
    title: "表配置管理",
    description: "管理数据库表的基础配置和元数据信息",
    href: "/metadata/tables",
    icon: Database,
    color: "text-blue-600"
  },
  {
    title: "业务术语",
    description: "维护业务术语表，支持自然语言查询理解",
    href: "/metadata/glossary",
    icon: BookOpen,
    color: "text-green-600"
  },
  {
    title: "关联配置",
    description: "配置表之间的关系和关联规则",
    href: "/metadata/relations",
    icon: GitBranch,
    color: "text-purple-600"
  },
  {
    title: "提示词配置",
    description: "配置AI提示词模板，优化查询生成效果",
    href: "/metadata/prompts",
    icon: MessageSquare,
    color: "text-orange-600"
  },
  {
    title: "数据主题",
    description: "按主题组织数据，支持业务场景分类",
    href: "/metadata/themes",
    icon: Palette,
    color: "text-pink-600"
  },
  {
    title: "AI助手",
    description: "智能对话助手，支持自然语言数据查询",
    href: "/agent",
    icon: Bot,
    color: "text-indigo-600"
  }
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        {/* 页面头部 */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            淘沙分析平台
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            基于AI的自然语言转SQL分析平台，让数据分析变得简单高效
          </p>
        </div>

        {/* 功能导航 */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-12">
          {navigationItems.map((item) => (
            <Card key={item.href} className="hover:shadow-lg transition-shadow cursor-pointer group">
              <Link href={item.href}>
                <CardHeader>
                  <div className="flex items-center space-x-3">
                    <item.icon className={`h-8 w-8 ${item.color} group-hover:scale-110 transition-transform`} />
                    <div>
                      <CardTitle className="text-lg">{item.title}</CardTitle>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm">
                    {item.description}
                  </CardDescription>
                </CardContent>
              </Link>
            </Card>
          ))}
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

        {/* 统计信息 */}
        <div className="mt-12 text-center">
          <div className="grid gap-4 md:grid-cols-4 max-w-4xl mx-auto">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-blue-600">100+</div>
                <p className="text-sm text-muted-foreground">数据表</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-green-600">50+</div>
                <p className="text-sm text-muted-foreground">业务术语</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-purple-600">1000+</div>
                <p className="text-sm text-muted-foreground">查询记录</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-orange-600">95%</div>
                <p className="text-sm text-muted-foreground">查询成功率</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

