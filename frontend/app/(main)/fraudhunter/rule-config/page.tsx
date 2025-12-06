'use client'

/**
 * FraudHunter 规则配置页面
 *
 * 版本: v2.2.0 (支持导入/导出)
 * 功能: 可视化规则配置，支持指标间比较、时间函数和规则导入导出
 */

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle2, FileJson, Info } from 'lucide-react'
import type { Indicator, RuleConfig } from '@/types/fraudhunter/rule'
import { RuleBuilder } from '@/components/fraudhunter/model/RuleBuilder'
import { RuleImportExport } from '@/components/fraudhunter/model/RuleImportExport'

export default function RuleConfigPage() {
  // 规则配置状态
  const [currentRule, setCurrentRule] = useState<RuleConfig | undefined>(undefined)
  // 用于强制重新渲染RuleBuilder的key
  const [builderKey, setBuilderKey] = useState(0)

  // 示例指标数据
  const sampleIndicators: Indicator[] = [
    {
      indicator_code: 'i_login_cnt_7d',
      indicator_name: '7天登录次数',
      data_type: 'int',
      description: '用户最近7天内的登录次数'
    },
    {
      indicator_code: 'i_user_age',
      indicator_name: '用户年龄',
      data_type: 'int',
      description: '用户注册年龄'
    },
    {
      indicator_code: 'i_user_status',
      indicator_name: '用户状态',
      data_type: 'string',
      description: '用户账户状态'
    },
    {
      indicator_code: 'i_tran_date',
      indicator_name: '交易时间',
      data_type: 'date',
      description: '交易发生时间'
    },
    {
      indicator_code: 'i_etl_date',
      indicator_name: '数据入库时间',
      data_type: 'date',
      description: '数据ETL处理时间'
    },
    {
      indicator_code: 'i_risk_score',
      indicator_name: '风险分数',
      data_type: 'float',
      description: '用户综合风险分数'
    },
    {
      indicator_code: 'i_device_type',
      indicator_name: '设备类型',
      data_type: 'string',
      description: '用户设备类型'
    },
    {
      indicator_code: 'i_is_vip',
      indicator_name: '是否VIP用户',
      data_type: 'bool',
      description: '用户是否为VIP'
    }
  ]

  // 处理规则变化
  const handleRuleChange = (newRule: RuleConfig) => {
    setCurrentRule(newRule)
  }

  // 处理规则导入
  const handleRuleImport = (importedRule: RuleConfig) => {
    setCurrentRule(importedRule)
    // 增加key值以强制RuleBuilder重新渲染
    setBuilderKey(prev => prev + 1)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">规则配置</h1>
          <p className="text-muted-foreground mt-2">
            可视化规则配置平台，支持规则导入导出
          </p>
        </div>
      </div>

      {/* 导入/导出功能区 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileJson className="h-5 w-5" />
            规则导入/导出
          </CardTitle>
        </CardHeader>
        <CardContent>
          {currentRule ? (
            <RuleImportExport
              currentRule={currentRule}
              onImport={handleRuleImport}
            />
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                请先配置规则，然后即可导出。或直接导入已有的规则配置。
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* 规则构建器 */}
      <RuleBuilder
        key={builderKey}
        indicators={sampleIndicators}
        initialRule={currentRule}
        onChange={handleRuleChange}
      />
    </div>
  )
}