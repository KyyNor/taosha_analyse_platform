'use client'

/**
 * 规则构建器组件
 *
 * 版本: v2.1.0 (支持值表达式)
 *
 * 功能：
 * - 支持嵌套规则组（AND/OR逻辑）
 * - 条件规则编辑（集成值表达式编辑器）
 * - 实时规则预览
 * - 规则验证和SQL生成预览
 */

import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Trash2, Plus, Code, CheckCircle2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  RuleConfig,
  GroupRule,
  ConditionRule,
  Indicator
} from '@/types/fraudhunter/rule'
import { ConditionRuleEditor } from './ConditionRuleEditor'
import { modelService } from '@/lib/services/fraudhunter/modelService'

interface RuleBuilderProps {
  indicators: Indicator[]
  initialRule?: RuleConfig
  onChange?: (rule: RuleConfig) => void
  readOnly?: boolean
}

export function RuleBuilder({ indicators, initialRule, onChange, readOnly = false }: RuleBuilderProps) {
  const [rule, setRule] = useState<RuleConfig>(initialRule || {
    logic: 'AND',
    rules: [
      {
        type: 'condition',
        indicator: indicators[0]?.indicator_code || '',
        operator: '>',
        value: { type: 'constant', value: 0 },
        left_function: undefined
      }
    ],
    output: {
      risk_level: 'medium',
      risk_score: 50,
      action: 'review',
      description: ''
    }
  })

  const [validation, setValidation] = useState<any>(null)
  const [sqlPreview, setSqlPreview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const updateRule = useCallback((newRule: RuleConfig) => {
    setRule(newRule)
    onChange?.(newRule)
  }, [onChange])

  // 添加条件规则
  const addConditionRule = useCallback((parentPath?: number[]) => {
    const newRule: ConditionRule = {
      type: 'condition',
      indicator: indicators[0]?.indicator_code || '',
      operator: '>',
      value: { type: 'constant', value: 0 },
      left_function: undefined
    }

    setRule(prevRule => {
      if (!parentPath) {
        // 添加到根级别
        return {
          ...prevRule,
          rules: [...prevRule.rules, newRule]
        }
      } else {
        // 添加到指定的规则组（暂未实现嵌套）
        return prevRule
      }
    })
  }, [indicators])

  // 添加规则组
  const addRuleGroup = useCallback(() => {
    const newGroup: GroupRule = {
      type: 'group',
      logic: 'AND',
      rules: [
        {
          type: 'condition',
          indicator: indicators[0]?.indicator_code || '',
          operator: '>',
          value: { type: 'constant', value: 0 },
          left_function: undefined
        }
      ]
    }

    setRule(prevRule => ({
      ...prevRule,
      rules: [...prevRule.rules, newGroup]
    }))
  }, [indicators])

  // 删除规则
  const removeRule = useCallback((index: number) => {
    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.filter((_, i) => i !== index)
    }))
  }, [])

  // 更新规则
  const updateRuleAtIndex = useCallback((index: number, updatedRule: ConditionRule | GroupRule) => {
    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.map((r, i) => i === index ? updatedRule : r)
    }))
  }, [])

  // 更新规则组的逻辑操作符
  const updateGroupLogic = useCallback((index: number, newLogic: 'AND' | 'OR') => {
    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.map((r, i) =>
        i === index && r.type === 'group' ? { ...r, logic: newLogic } : r
      )
    }))
  }, [])

  // 更新主逻辑操作符
  const updateLogic = useCallback((newLogic: 'AND' | 'OR') => {
    updateRule({ ...rule, logic: newLogic })
  }, [rule, updateRule])

  // 向规则组添加条件
  const addConditionToGroup = useCallback((groupIndex: number) => {
    const newCondition: ConditionRule = {
      type: 'condition',
      indicator: indicators[0]?.indicator_code || '',
      operator: '>',
      value: { type: 'constant', value: 0 },
      left_function: undefined
    }

    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.map((r, i) =>
        i === groupIndex && r.type === 'group'
          ? { ...r, rules: [...r.rules, newCondition] }
          : r
      )
    }))
  }, [indicators])

  // 从规则组删除条件
  const removeConditionFromGroup = useCallback((groupIndex: number, conditionIndex: number) => {
    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.map((r, i) =>
        i === groupIndex && r.type === 'group'
          ? { ...r, rules: r.rules.filter((_, cIndex) => cIndex !== conditionIndex) }
          : r
      )
    }))
  }, [])

  // 更新规则组内的条件
  const updateConditionInGroup = useCallback((groupIndex: number, conditionIndex: number, updatedCondition: ConditionRule) => {
    setRule(prevRule => ({
      ...prevRule,
      rules: prevRule.rules.map((r, i) =>
        i === groupIndex && r.type === 'group'
          ? { ...r, rules: r.rules.map((c, cIndex) => cIndex === conditionIndex ? updatedCondition : c) }
          : r
      )
    }))
  }, [])

  // 验证规则
  const validateRule = useCallback(async () => {
    setLoading(true)
    try {
      const result = await modelService.validateRule(rule)
      setValidation(result)
      return result
    } catch (error) {
      console.error('规则验证失败:', error)
      setValidation({ valid: false, errors: [(error as Error).message] })
      return { valid: false, errors: [(error as Error).message] }
    } finally {
      setLoading(false)
    }
  }, [rule])

  // SQL预览
  const previewSQL = useCallback(async () => {
    setLoading(true)
    try {
      const result = await modelService.previewSQL(rule)
      setSqlPreview(result)
      return result
    } catch (error) {
      console.error('SQL预览失败:', error)
      alert('SQL预览失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }, [rule])

  return (
    <div className="space-y-6">
      {/* 规则构建器头部 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>规则构建器</span>
            <div className="flex items-center gap-2">
              {/* 逻辑操作符选择 */}
              <Select value={rule.logic} onValueChange={(v: 'AND' | 'OR') => updateLogic(v)}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AND">AND</SelectItem>
                  <SelectItem value="OR">OR</SelectItem>
                </SelectContent>
              </Select>

              {/* 验证和预览按钮 */}
              <Button
                onClick={validateRule}
                disabled={loading}
                variant="outline"
                size="sm"
              >
                <CheckCircle2 className="h-4 w-4 mr-1" />
                验证
              </Button>
              <Button
                onClick={previewSQL}
                disabled={loading}
                variant="outline"
                size="sm"
              >
                <Code className="h-4 w-4 mr-1" />
                SQL
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* 规则列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <span>规则条件</span>
            <div className="flex gap-2">
              <Button onClick={() => addConditionRule()} disabled={readOnly} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                条件
              </Button>
              <Button onClick={addRuleGroup} disabled={readOnly} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                规则组
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {rule.rules.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              暂无规则条件，点击上方按钮添加
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              {rule.rules.map((ruleItem, index) => (
                <div key={index} className="relative">
                  {ruleItem.type === 'condition' ? (
                    <div className="flex items-center gap-2 border-b last:border-b-0 py-2 px-4">
                      {/* 序号 */}
                      <div className="flex-shrink-0 w-12 text-center">
                        <Badge variant="secondary" className="text-xs">
                          {index + 1}
                        </Badge>
                      </div>

                      {/* 逻辑连接符提示（仅显示不可编辑） */}
                      {index > 0 && (
                        <div className="flex-shrink-0">
                          <Badge variant="outline" className="text-xs">
                            {rule.logic}
                          </Badge>
                        </div>
                      )}

                      {/* 条件编辑器 */}
                      <div className="flex-1">
                        <ConditionRuleEditor
                          rule={ruleItem}
                          indicators={indicators}
                          onChange={(updatedRule) => updateRuleAtIndex(index, updatedRule)}
                        />
                      </div>

                      {/* 删除按钮 */}
                      <div className="flex-shrink-0">
                        {!readOnly && (
                          <Button
                            onClick={() => removeRule(index)}
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="border-t pt-4 pb-4">
                      <div className="flex items-center gap-2 mb-4">
                        {/* 规则组序号和删除按钮 */}
                        <div className="flex-shrink-0 w-12 text-center">
                          <Badge variant="secondary" className="text-xs">
                            {index + 1}
                          </Badge>
                        </div>

                        {index > 0 && (
                          <div className="flex-shrink-0">
                            <Badge variant="outline" className="text-xs">
                              {rule.logic}
                            </Badge>
                          </div>
                        )}

                        <div className="flex items-center gap-2 bg-muted/30 px-3 py-2 rounded-lg flex-1">
                          <Badge variant="outline">规则组</Badge>
                          <Select
                            value={ruleItem.logic}
                            onValueChange={(v: 'AND' | 'OR') => updateGroupLogic(index, v)}
                          >
                            <SelectTrigger className="w-[80px] h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="AND">AND</SelectItem>
                              <SelectItem value="OR">OR</SelectItem>
                            </SelectContent>
                          </Select>

                          <Button
                            onClick={() => addConditionToGroup(index)}
                            disabled={readOnly}
                            variant="outline"
                            size="sm"
                          >
                            <Plus className="h-3 w-3 mr-1" />
                            添加条件
                          </Button>

                          <div className="text-sm text-muted-foreground ml-auto">
                            {ruleItem.rules.length} 个条件
                          </div>

                          {!readOnly && (
                            <Button
                              onClick={() => removeRule(index)}
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* 规则组内的条件 */}
                      <div className="ml-16 space-y-0 border-l-2 border-muted">
                        {ruleItem.rules.filter(r => r.type === 'condition').map((condition, conditionIndex) => {
                          const originalIndex = ruleItem.rules.indexOf(condition)
                          return (
                          <div key={originalIndex} className="flex items-center gap-2 border-l-2 border-background pl-4 -ml-[2px]">
                            {/* 条件序号 */}
                            <div className="flex-shrink-0 w-12 text-center">
                              <Badge variant="outline" className="text-xs">
                                {originalIndex + 1}
                              </Badge>
                            </div>

                            {/* 逻辑连接符（组内第一个条件之后才显示） */}
                            {originalIndex > 0 && (
                              <div className="flex-shrink-0">
                                <Badge variant="outline" className="text-xs">
                                  {ruleItem.logic}
                                </Badge>
                              </div>
                            )}

                            {/* 条件编辑器 */}
                            <div className="flex-1">
                              <ConditionRuleEditor
                                rule={condition as ConditionRule}
                                indicators={indicators}
                                onChange={(updatedCondition) =>
                                  updateConditionInGroup(index, originalIndex, updatedCondition)
                                }
                              />
                            </div>

                            {/* 删除按钮 */}
                            <div className="flex-shrink-0">
                              {!readOnly && (
                                <Button
                                  onClick={() => removeConditionFromGroup(index, originalIndex)}
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </div>
                          )
                        })}

                        {ruleItem.rules.length === 0 && (
                          <div className="text-center text-muted-foreground py-4 ml-16">
                            规则组为空，点击"添加条件"按钮添加
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 逻辑操作符说明 */}
          {rule.rules.length > 1 && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                所有条件使用 <Badge variant="outline">{rule.logic}</Badge> 逻辑连接
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 验证结果 */}
      {validation && (
        <Card className={cn(
          "border-2",
          validation.valid ? "border-green-200 bg-green-50/50" : "border-red-200 bg-red-50/50"
        )}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              {validation.valid ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  验证通过
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  验证失败
                </>
              )}
            </CardTitle>
          </CardHeader>
          {validation.valid ? (
            <CardContent className="text-sm">
              <div className="space-y-1">
                <p>✅ 规则语法正确</p>
                <p>✅ 提取的指标: {validation.extracted_indicators?.join(', ') || '无'}</p>
              </div>
            </CardContent>
          ) : (
            <CardContent className="text-sm">
              <div className="space-y-1 text-red-700">
                {validation.errors?.map((error: string, index: number) => (
                  <p key={index}>❌ {error}</p>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* SQL预览结果 */}
      {sqlPreview && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">SQL预览</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <h4 className="text-sm font-medium mb-1">SQL表达式:</h4>
                <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                  {sqlPreview.sql_expression}
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-1">规则摘要:</h4>
                <div className="text-xs space-y-1">
                  <p>• 规则总数: {sqlPreview.rule_summary?.total_rules}</p>
                  <p>• 最大深度: {sqlPreview.rule_summary?.max_depth}</p>
                  <p>• 指标数量: {sqlPreview.rule_summary?.indicator_count}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}