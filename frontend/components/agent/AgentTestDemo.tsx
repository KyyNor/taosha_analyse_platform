"use client";

import React from "react";
import { useAgentState } from "@/lib/state/agent";
import { Button } from "@/components/ui/button";
import { ChatMessage } from "@/lib/state/agent";

export function AgentTestDemo() {
  const { clearMessages, toggleThinkingChain, toggleToolCalls, addMessage } = useAgentState();

  // 添加测试消息
  const addTestMessages = () => {
    // 添加用户消息
    addMessage('user', '你好，请帮我分析一下销售数据');

    // 添加助手消息（包含思维链和工具调用）
    addMessage('assistant', `您好！我来帮您分析销售数据。

## 数据分析结果

根据您的销售数据，我发现了以下几个关键趋势：

1. **销售额增长**: 本月销售额相比上月增长了 15%
2. **热门产品**: 产品A和产品B的销售额最高
3. **地区分布**: 华东地区的销售额占总体 40%

### 详细报告

| 产品 | 销售额 | 增长率 |
|------|--------|--------|
| 产品A | ¥50,000 | +20% |
| 产品B | ¥35,000 | +15% |
| 产品C | ¥20,000 | +5% |

如果您需要更详细的分析或有其他问题，请告诉我！`, {
      thinking: `用户想了解销售数据分析。我需要：
1. 理解用户的具体需求
2. 检查是否有销售数据可用
3. 使用数据分析工具查询相关数据
4. 分析数据趋势和模式
5. 生成清晰的报告

首先我应该查询销售数据库获取最近的数据。`,
      tool_calls: [
        {
          id: 'tool_1',
          name: 'query_database',
          arguments: {
            query: 'SELECT * FROM sales_data WHERE date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)',
            database: 'sales'
          },
          result: {
            rows: 156,
            total_sales: 105000,
            top_products: ['产品A', '产品B', '产品C']
          },
          status: 'completed'
        },
        {
          id: 'tool_2',
          name: 'calculate_growth_rate',
          arguments: {
            current_month: 105000,
            previous_month: 91300
          },
          result: {
            growth_rate: 0.15,
            percentage: '15%'
          },
          status: 'completed'
        }
      ]
    });
  };

  return (
    <div className="p-4 border-b bg-background/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Agent测试控制</span>
          <span className="text-xs text-muted-foreground">(开发阶段)</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleThinkingChain}
          >
            切换思维链
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={toggleToolCalls}
          >
            切换工具调用
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={addTestMessages}
          >
            添加测试消息
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={clearMessages}
          >
            清空消息
          </Button>
        </div>
      </div>

      <p className="text-xs text-muted-foreground mt-2">
        • 点击"添加测试消息"可以看到思维链和工具调用的展示效果
        • 使用侧边栏开关控制思维链和工具调用的显示
        • 在实际使用中，消息会通过后端API获取
      </p>
    </div>
  );
}