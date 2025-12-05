'use client'

/**
 * FraudHunter 规则配置页面
 *
 * 版本: v2.1.0 (支持值表达式)
 * 功能: 可视化规则配置，支持指标间比较和时间函数
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2 } from 'lucide-react'
import type { Indicator } from '@/types/fraudhunter/rule'
import { RuleBuilder } from '@/components/fraudhunter/model/RuleBuilder'

export default function RuleConfigPage() {
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

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">规则配置</h1>
          <p className="text-muted-foreground mt-2">
            可视化规则配置平台
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            系统正常
          </span>
        </Badge>
      </div>

      {/* 规则构建器 */}
      <RuleBuilder
        indicators={sampleIndicators}
      />
    </div>
  )
}