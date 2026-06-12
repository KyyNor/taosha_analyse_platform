'use client'

/**
 * 规则构建器组件
 *
 * 版本: v2.2.0 (支持多层嵌套规则组)
 *
 * 功能：
 * - 支持无限层级嵌套规则组（AND/OR逻辑）
 * - 条件规则编辑（集成值表达式编辑器）
 * - 实时规则预览
 * - 规则验证和SQL生成预览
 */

import { useState, useCallback, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Trash2, Plus, Code, CheckCircle2, AlertCircle, Info, Layers } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import {
  RuleConfig,
  GroupRule,
  ConditionRule,
  ModelReferenceRule,
  Indicator,
  Rule
} from '@/types/fraudhunter/rule'
import type { RiskControlModel } from '@/types/fraudhunter/risk-control-model'
import { ConditionRuleEditor } from './ConditionRuleEditor'
import { modelService } from '@/lib/services/fraudhunter/modelService'

interface RuleBuilderProps {
  indicators: Indicator[]
  initialRule?: RuleConfig
  onChange?: (rule: RuleConfig) => void
  readOnly?: boolean
  prefixModels?: RiskControlModel[]
}

// 路径类型：用于定位嵌套规则
type RulePath = number[]

// 辅助函数：根据路径获取规则
function getRuleAtPath(rules: Rule[], path: RulePath): Rule | null {
  if (path.length === 0) return null

  let current: Rule | null = rules[path[0]] || null

  for (let i = 1; i < path.length; i++) {
    if (!current || current.type !== 'group') return null
    current = current.rules[path[i]] || null
  }

  return current
}

// 辅助函数：根据路径更新规则
function updateRuleAtPath(rules: Rule[], path: RulePath, updater: (rule: Rule) => Rule): Rule[] {
  if (path.length === 0) return rules

  const [index, ...restPath] = path

  if (restPath.length === 0) {
    // 更新当前层级的规则
    return rules.map((rule, i) => i === index ? updater(rule) : rule)
  } else {
    // 递归更新嵌套规则
    return rules.map((rule, i) => {
      if (i === index && rule.type === 'group') {
        return {
          ...rule,
          rules: updateRuleAtPath(rule.rules, restPath, updater)
        }
      }
      return rule
    })
  }
}

// 辅助函数：根据路径删除规则
function removeRuleAtPath(rules: Rule[], path: RulePath): Rule[] {
  if (path.length === 0) return rules

  const [index, ...restPath] = path

  if (restPath.length === 0) {
    // 删除当前层级的规则
    return rules.filter((_, i) => i !== index)
  } else {
    // 递归删除嵌套规则
    return rules.map((rule, i) => {
      if (i === index && rule.type === 'group') {
        return {
          ...rule,
          rules: removeRuleAtPath(rule.rules, restPath)
        }
      }
      return rule
    })
  }
}

// 辅助函数：根据路径添加规则
function addRuleAtPath(rules: Rule[], path: RulePath, newRule: Rule): Rule[] {
  if (path.length === 0) {
    // 添加到根级别
    return [...rules, newRule]
  }

  const [index, ...restPath] = path

  if (restPath.length === 0) {
    // 添加到当前规则组
    return rules.map((rule, i) => {
      if (i === index && rule.type === 'group') {
        return {
          ...rule,
          rules: [...rule.rules, newRule]
        }
      }
      return rule
    })
  } else {
    // 递归添加到嵌套规则组
    return rules.map((rule, i) => {
      if (i === index && rule.type === 'group') {
        return {
          ...rule,
          rules: addRuleAtPath(rule.rules, restPath, newRule)
        }
      }
      return rule
    })
  }
}

const createDefaultRule = (indicatorCode?: string): RuleConfig => ({
  logic: 'AND',
  rules: [
    {
      type: 'condition',
      indicator: indicatorCode || '',
      operator: '>',
      value: { type: 'constant', value: 0 },
      left_function: undefined
    }
  ]
})

// 递归规则组渲染器
interface RuleGroupRendererProps {
  rules: Rule[]
  parentPath: RulePath
  parentLogic: 'AND' | 'OR'
  indicators: Indicator[]
  depth: number
  readOnly: boolean
  onUpdate: (path: RulePath, rule: Rule) => void
  onRemove: (path: RulePath) => void
  onAddCondition: (path: RulePath) => void
  onAddGroup: (path: RulePath) => void
  onAddModelRef: (path: RulePath) => void
  prefixModels: RiskControlModel[]
}

function RuleGroupRenderer({
  rules,
  parentPath,
  parentLogic,
  indicators,
  depth,
  readOnly,
  onUpdate,
  onRemove,
  onAddCondition,
  onAddGroup,
  onAddModelRef,
  prefixModels
}: RuleGroupRendererProps) {
  const indentWidth = depth * 16 // 每层缩进16px

  return (
    <div className="space-y-0">
      {rules.map((rule, index) => {
        const currentPath = [...parentPath, index]

        return (
          <div key={index} className="relative">
            {rule.type === 'condition' ? (
              // 条件规则渲染
              <div className="flex items-center gap-2 border-b last:border-b-0 py-2 px-4" style={{ paddingLeft: `${indentWidth + 16}px` }}>
                {/* 序号 */}
                <div className="flex-shrink-0 w-12 text-center">
                  <Badge variant={depth > 0 ? "outline" : "secondary"} className="text-xs">
                    {index + 1}
                  </Badge>
                </div>

                {/* 逻辑连接符 */}
                {index > 0 && (
                  <div className="flex-shrink-0">
                    <Badge variant="outline" className="text-xs">
                      {parentLogic}
                    </Badge>
                  </div>
                )}

                {/* 条件编辑器 */}
                <div className="flex-1">
                  <ConditionRuleEditor
                    rule={rule}
                    indicators={indicators}
                    onChange={(updatedRule) => onUpdate(currentPath, updatedRule)}
                  />
                </div>

                {/* 删除按钮 */}
                <div className="flex-shrink-0">
                  {!readOnly && (
                    <Button
                      onClick={() => onRemove(currentPath)}
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            ) : rule.type === 'model_ref' ? (
              <div className="flex items-center gap-2 border-b last:border-b-0 py-2 px-4 bg-blue-50/40" style={{ paddingLeft: `${indentWidth + 16}px` }}>
                <div className="flex-shrink-0 w-12 text-center">
                  <Badge variant={depth > 0 ? "outline" : "secondary"} className="text-xs">
                    {index + 1}
                  </Badge>
                </div>

                {index > 0 && (
                  <div className="flex-shrink-0">
                    <Badge variant="outline" className="text-xs">
                      {parentLogic}
                    </Badge>
                  </div>
                )}

                <div className="flex items-center gap-2 flex-1">
                  <Badge variant="outline" className="gap-1">
                    <Layers className="h-3 w-3" />
                    前缀模型
                  </Badge>
                  <Select
                    value={String(rule.model_id)}
                    onValueChange={(value) => {
                      const selected = prefixModels.find(model => model.id === Number(value))
                      if (!selected) return
                      onUpdate(currentPath, {
                        type: 'model_ref',
                        model_id: selected.id,
                        model_code: selected.model_code,
                        model_name: selected.model_name
                      })
                    }}
                    disabled={readOnly}
                  >
                    <SelectTrigger className="min-w-[280px] h-8">
                      <SelectValue placeholder="选择前缀模型" />
                    </SelectTrigger>
                    <SelectContent>
                      {prefixModels.map((model) => (
                        <SelectItem key={model.id} value={String(model.id)}>
                          {model.model_name} ({model.model_code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {!readOnly && (
                  <Button
                    onClick={() => onRemove(currentPath)}
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ) : (
              // 规则组渲染（递归）
              <div className="border-t pt-4 pb-4" style={{ paddingLeft: `${indentWidth}px` }}>
                <div className="flex items-center gap-2 mb-4">
                  {/* 规则组序号 */}
                  <div className="flex-shrink-0 w-12 text-center">
                    <Badge variant={depth > 0 ? "outline" : "secondary"} className="text-xs">
                      {index + 1}
                    </Badge>
                  </div>

                  {/* 逻辑连接符 */}
                  {index > 0 && (
                    <div className="flex-shrink-0">
                      <Badge variant="outline" className="text-xs">
                        {parentLogic}
                      </Badge>
                    </div>
                  )}

                  {/* 规则组控制区 */}
                  <div className="flex items-center gap-2 bg-muted/30 px-3 py-2 rounded-lg flex-1">
                    <Badge variant="outline">规则组</Badge>

                    {/* 规则组逻辑选择器 */}
                    <Select
                      value={rule.logic}
                      onValueChange={(v: 'AND' | 'OR') =>
                        onUpdate(currentPath, { ...rule, logic: v })
                      }
                    >
                      <SelectTrigger className="w-[80px] h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="AND">AND</SelectItem>
                        <SelectItem value="OR">OR</SelectItem>
                      </SelectContent>
                    </Select>

                    {/* 添加条件按钮 */}
                    <Button
                      onClick={() => onAddCondition(currentPath)}
                      disabled={readOnly}
                      variant="outline"
                      size="sm"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      添加条件
                    </Button>

                    {/* 添加规则组按钮 */}
                    <Button
                      onClick={() => onAddGroup(currentPath)}
                      disabled={readOnly}
                      variant="outline"
                      size="sm"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      添加规则组
                    </Button>

                    <Button
                      onClick={() => onAddModelRef(currentPath)}
                      disabled={readOnly || prefixModels.length === 0}
                      variant="outline"
                      size="sm"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      前缀模型
                    </Button>

                    {/* 规则数量提示 */}
                    <div className="text-sm text-muted-foreground ml-auto">
                      {rule.rules.length} 个规则
                    </div>

                    {/* 删除规则组按钮 */}
                    {!readOnly && (
                      <Button
                        onClick={() => onRemove(currentPath)}
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* 递归渲染规则组内的规则 */}
                {rule.rules.length > 0 ? (
                  <div className="ml-16 border-l-2 border-muted">
                    <RuleGroupRenderer
                      rules={rule.rules}
                      parentPath={currentPath}
                      parentLogic={rule.logic}
                      indicators={indicators}
                      depth={depth + 1}
                      readOnly={readOnly}
                      onUpdate={onUpdate}
                      onRemove={onRemove}
                      onAddCondition={onAddCondition}
                      onAddGroup={onAddGroup}
                      onAddModelRef={onAddModelRef}
                      prefixModels={prefixModels}
                    />
                  </div>
                ) : (
                  <Alert className="ml-16 border-dashed">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      规则组为空，点击"添加条件"或"添加规则组"按钮
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function RuleBuilder({ indicators, initialRule, onChange, readOnly = false, prefixModels = [] }: RuleBuilderProps) {
  const [rule, setRule] = useState<RuleConfig>(() =>
    initialRule || createDefaultRule(indicators[0]?.indicator_code)
  )

  const setRuleAndNotify = useCallback((
    updater: RuleConfig | ((prev: RuleConfig) => RuleConfig)
  ) => {
    setRule(prev => {
      const next = typeof updater === 'function'
        ? (updater as (prev: RuleConfig) => RuleConfig)(prev)
        : updater
      onChange?.(next)
      return next
    })
  }, [onChange])

  useEffect(() => {
    if (initialRule) {
      setRule(initialRule)
    }
  }, [initialRule])

  const [validation, setValidation] = useState<any>(null)
  const [sqlPreview, setSqlPreview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // 添加条件规则（支持嵌套路径）
  const handleAddCondition = useCallback((path: RulePath) => {
    const newCondition: ConditionRule = {
      type: 'condition',
      indicator: indicators[0]?.indicator_code || '',
      operator: '>',
      value: { type: 'constant', value: 0 },
      left_function: undefined
    }

    setRuleAndNotify(prevRule => ({
      ...prevRule,
      rules: addRuleAtPath(prevRule.rules, path, newCondition)
    }))
  }, [indicators, setRuleAndNotify])

  // 添加规则组（支持嵌套路径）
  const handleAddGroup = useCallback((path: RulePath) => {
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

    setRuleAndNotify(prevRule => ({
      ...prevRule,
      rules: addRuleAtPath(prevRule.rules, path, newGroup)
    }))
  }, [indicators, setRuleAndNotify])

  const handleAddModelRef = useCallback((path: RulePath) => {
    const firstPrefixModel = prefixModels[0]
    if (!firstPrefixModel) {
      toast.error('暂无可引用的前缀模型')
      return
    }

    const newModelRef: ModelReferenceRule = {
      type: 'model_ref',
      model_id: firstPrefixModel.id,
      model_code: firstPrefixModel.model_code,
      model_name: firstPrefixModel.model_name
    }

    setRuleAndNotify(prevRule => ({
      ...prevRule,
      rules: addRuleAtPath(prevRule.rules, path, newModelRef)
    }))
  }, [prefixModels, setRuleAndNotify])

  // 删除规则（支持嵌套路径）
  const handleRemove = useCallback((path: RulePath) => {
    setRuleAndNotify(prevRule => ({
      ...prevRule,
      rules: removeRuleAtPath(prevRule.rules, path)
    }))
  }, [setRuleAndNotify])

  // 更新规则（支持嵌套路径）
  const handleUpdate = useCallback((path: RulePath, updatedRule: Rule) => {
    setRuleAndNotify(prevRule => ({
      ...prevRule,
      rules: updateRuleAtPath(prevRule.rules, path, () => updatedRule)
    }))
  }, [setRuleAndNotify])

  // 更新主逻辑操作符
  const updateLogic = useCallback((newLogic: 'AND' | 'OR') => {
    setRuleAndNotify(prev => ({ ...prev, logic: newLogic }))
  }, [setRuleAndNotify])

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
      toast.error('SQL预览失败: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }, [rule])

  return (
    <div className="space-y-6">
      {/* 规则列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <span>规则条件</span>
            <div className="flex gap-2">
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

              <Button onClick={() => handleAddCondition([])} disabled={readOnly} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                条件
              </Button>
              <Button onClick={() => handleAddGroup([])} disabled={readOnly} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                规则组
              </Button>
              <Button onClick={() => handleAddModelRef([])} disabled={readOnly || prefixModels.length === 0} variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                前缀模型
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {rule.rules.length === 0 ? (
            <Alert className="border-dashed">
              <Info className="h-4 w-4" />
              <AlertDescription>
                暂无规则条件，点击上方按钮添加
              </AlertDescription>
            </Alert>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <RuleGroupRenderer
                rules={rule.rules}
                parentPath={[]}
                parentLogic={rule.logic}
                indicators={indicators}
                depth={0}
                readOnly={readOnly}
                onUpdate={handleUpdate}
                onRemove={handleRemove}
                onAddCondition={handleAddCondition}
                onAddGroup={handleAddGroup}
                onAddModelRef={handleAddModelRef}
                prefixModels={prefixModels}
              />
            </div>
          )}

          {/* 逻辑操作符说明 */}
          {rule.rules.length > 1 && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm text-muted-foreground">
                所有根级别规则使用 <Badge variant="outline">{rule.logic}</Badge> 逻辑连接
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
