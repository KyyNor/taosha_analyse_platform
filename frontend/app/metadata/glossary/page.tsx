'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen } from "lucide-react";
import Layout from "@/components/layout/Layout";

export default function GlossaryPage() {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold tracking-tight mb-4">业务术语</h1>
          <p className="text-lg text-muted-foreground">维护业务术语表，支持自然语言查询理解</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BookOpen className="h-5 w-5" />
              <span>业务术语管理</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-12">
              <p className="text-muted-foreground">该页面正在开发中，敬请期待...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}