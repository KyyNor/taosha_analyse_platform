'use client'

/**
 * FraudHunter 规则引擎页面
 *
 * 版本: v2.0.0
 * 功能: 可视化规则配置和测试
 */

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle2, Code, Play, Settings } from 'lucide-react'
import { modelService } from '@/lib/services/fraudhunter/modelService'
import type { RuleConfig } from '@/types/fraudhunter/rule'

export default function RuleEnginePage() {
  const [loading, setLoading] = useState(false)
  const [healthStatus, setHealthStatus] = useState<any>(null)

  // 测试规则配置
  const testRuleConfig: RuleConfig = {
    logic: 'AND',
    rules: [
      {
        type: 'condition',
        indicator: 'i_login_cnt_7d',
        operator: '>',
        value: 10
      },
      {
        type: 'condition',
        indicator: 'i_user_status',
        operator: 'in',
        value: ['suspended', 'banned']
      }
    ],
    output: {
      risk_level: 'high',
      risk_score: 85,
      action: 'review',
      description: '高风险登录行为'
    }
  }

  // 检查健康状态
  const checkHealth = async () => {
    setLoading(true)
    try {
      const result = await modelService.healthCheck()
      setHealthStatus(result)
      console.log('健康检查结果:', result)
    } catch (error) {
      console.error('健康检查失败:', error)
      alert('健康检查失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 测试规则验证
  const testValidation = async () => {
    setLoading(true)
    try {
      const result = await modelService.validateRule(testRuleConfig)
      console.log('验证结果:', result)

      if (result.valid) {
        alert(`验证通过！\n提取的指标: ${result.extracted_indicators.join(', ')}`)
      } else {
        alert(`验证失败！\n错误: ${result.errors.join('\n')}`)
      }
    } catch (error) {
      console.error('验证失败:', error)
      alert('验证失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 测试SQL预览
  const testSQLPreview = async () => {
    setLoading(true)
    try {
      const result = await modelService.previewSQL(testRuleConfig)
      console.log('SQL预览结果:', result)

      alert(`SQL表达式:\n${result.sql_expression}\n\n规则摘要:\n- 规则总数: ${result.rule_summary.total_rules}\n- 最大深度: ${result.rule_summary.max_depth}\n- 指标数量: ${result.rule_summary.indicator_count}`)
    } catch (error) {
      console.error('SQL预览失败:', error)
      alert('SQL预览失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 测试规则评估
  const testEvaluation = async () => {
    setLoading(true)
    try {
      const result = await modelService.evaluateRule(testRuleConfig, {
        i_login_cnt_7d: 15,
        i_user_status: 'suspended'
      })
      console.log('评估结果:', result)

      if (result.is_hit) {
        alert(`规则命中！\n风险等级: ${result.output?.risk_level}\n风险分数: ${result.output?.risk_score}\n处理动作: ${result.output?.action}`)
      } else {
        alert('规则未命中')
      }
    } catch (error) {
      console.error('评估失败:', error)
      alert('评估失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">规则引擎</h1>
          <p className="text-muted-foreground mt-2">
            可视化规则配置和测试平台 v2.0.0
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          {healthStatus ? (
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              服务正常
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <AlertCircle className="h-4 w-4 text-yellow-500" />
              未检查
            </span>
          )}
        </Badge>
      </div>

      {/* 功能说明卡片 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            核心功能
          </CardTitle>
          <CardDescription>
            支持10种操作符：基础比较(6种) + 集合操作(2种) + 正则匹配(2种)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-2">基础比较</h3>
              <div className="flex flex-wrap gap-1">
                {['>', '>=', '<', '<=', '=', '!='].map(op => (
                  <Badge key={op} variant="secondary">{op}</Badge>
                ))}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-2">集合操作</h3>
              <div className="flex flex-wrap gap-1">
                {['in', 'not in'].map(op => (
                  <Badge key={op} variant="secondary">{op}</Badge>
                ))}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-2">正则匹配</h3>
              <div className="flex flex-wrap gap-1">
                {['regexp', 'not regexp'].map(op => (
                  <Badge key={op} variant="secondary">{op}</Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 快速测试区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            快速测试
          </CardTitle>
          <CardDescription>
            测试规则引擎的核心功能
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button
              onClick={checkHealth}
              disabled={loading}
              variant="outline"
              className="h-20"
            >
              <div className="flex flex-col items-center gap-2">
                <Settings className="h-5 w-5" />
                <span>健康检查</span>
              </div>
            </Button>

            <Button
              onClick={testValidation}
              disabled={loading}
              variant="outline"
              className="h-20"
            >
              <div className="flex flex-col items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                <span>测试规则验证</span>
              </div>
            </Button>

            <Button
              onClick={testSQLPreview}
              disabled={loading}
              variant="outline"
              className="h-20"
            >
              <div className="flex flex-col items-center gap-2">
                <Code className="h-5 w-5" />
                <span>测试SQL生成</span>
              </div>
            </Button>

            <Button
              onClick={testEvaluation}
              disabled={loading}
              variant="outline"
              className="h-20"
            >
              <div className="flex flex-col items-center gap-2">
                <Play className="h-5 w-5" />
                <span>测试规则评估</span>
              </div>
            </Button>
          </div>

          {loading && (
            <div className="mt-4 text-center text-muted-foreground">
              处理中...
            </div>
          )}
        </CardContent>
      </Card>

      {/* 测试规则配置展示 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            测试规则配置
          </CardTitle>
          <CardDescription>
            用于测试的规则配置示例
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
            {JSON.stringify(testRuleConfig, null, 2)}
          </pre>
        </CardContent>
      </Card>

      {/* 开发说明 */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-sm">开发说明</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>📝 待实现的组件：</p>
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>RuleBuilder - 主规则构建器（支持嵌套规则组）</li>
            <li>RuleOutputEditor - 输出配置编辑器</li>
            <li>RulePreview - 规则预览组件</li>
            <li>完整的规则管理界面（CRUD操作）</li>
          </ul>
          <p className="mt-4">
            📚 参考文档：
            <code className="ml-2 bg-muted px-2 py-1 rounded">
              QUICKSTART_RULE_ENGINE.md
            </code>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
