'use client'

/**
 * 规则配置导入/导出组件
 *
 * 功能：
 * - 导出规则配置为JSON文件
 * - 从JSON文件导入规则配置
 * - JSON格式与数据库存储格式一致（RuleConfig）
 */

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Download, Upload, FileJson, AlertCircle, CheckCircle2 } from 'lucide-react'
import { RuleConfig } from '@/types/fraudhunter/rule'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface RuleImportExportProps {
  currentRule: RuleConfig
  onImport: (rule: RuleConfig) => void
  onExport?: (rule: RuleConfig) => void
}

export function RuleImportExport({ currentRule, onImport, onExport }: RuleImportExportProps) {
  const [importError, setImportError] = useState<string | null>(null)
  const [importSuccess, setImportSuccess] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  /**
   * 导出规则配置为JSON文件
   */
  const handleExport = () => {
    try {
      // 生成时间戳
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `rule-config-${timestamp}.json`

      // 将规则配置转换为JSON字符串（格式化输出）
      const jsonContent = JSON.stringify(currentRule, null, 2)

      // 创建Blob对象
      const blob = new Blob([jsonContent], { type: 'application/json' })

      // 创建下载链接
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename

      // 触发下载
      document.body.appendChild(link)
      link.click()

      // 清理
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      // 触发自定义导出回调
      onExport?.(currentRule)

      console.log('规则配置已导出:', filename)
    } catch (error) {
      console.error('导出失败:', error)
      toast.error('导出失败: ' + (error as Error).message)
    }
  }

  /**
   * 验证导入的规则配置
   */
  const validateRuleConfig = (data: any): { valid: boolean; error?: string } => {
    // 检查必需字段
    if (!data || typeof data !== 'object') {
      return { valid: false, error: '无效的JSON格式' }
    }

    if (!data.logic || !['AND', 'OR'].includes(data.logic)) {
      return { valid: false, error: 'logic字段必须为AND或OR' }
    }

    if (!Array.isArray(data.rules)) {
      return { valid: false, error: 'rules字段必须是数组' }
    }

    if (!data.output || typeof data.output !== 'object') {
      return { valid: false, error: '缺少output配置' }
    }

    // 验证output字段
    const output = data.output
    if (!output.risk_level || !['low', 'medium', 'high', 'critical'].includes(output.risk_level)) {
      return { valid: false, error: 'output.risk_level必须为low/medium/high/critical之一' }
    }

    if (typeof output.risk_score !== 'number' || output.risk_score < 0 || output.risk_score > 100) {
      return { valid: false, error: 'output.risk_score必须是0-100之间的数字' }
    }

    // 递归验证规则
    const validateRules = (rules: any[]): { valid: boolean; error?: string } => {
      for (const rule of rules) {
        if (!rule.type || !['condition', 'group'].includes(rule.type)) {
          return { valid: false, error: 'rule.type必须为condition或group' }
        }

        if (rule.type === 'condition') {
          if (!rule.indicator || typeof rule.indicator !== 'string') {
            return { valid: false, error: '条件规则缺少indicator字段' }
          }
          if (!rule.operator || typeof rule.operator !== 'string') {
            return { valid: false, error: '条件规则缺少operator字段' }
          }
          if (rule.value === undefined || rule.value === null) {
            return { valid: false, error: '条件规则缺少value字段' }
          }
          // 验证值表达式
          if (typeof rule.value !== 'object' || !rule.value.type) {
            return { valid: false, error: '条件规则的value必须是值表达式对象' }
          }
        } else if (rule.type === 'group') {
          if (!rule.logic || !['AND', 'OR'].includes(rule.logic)) {
            return { valid: false, error: '规则组的logic字段必须为AND或OR' }
          }
          if (!Array.isArray(rule.rules)) {
            return { valid: false, error: '规则组的rules字段必须是数组' }
          }
          // 递归验证嵌套规则
          const nestedResult = validateRules(rule.rules)
          if (!nestedResult.valid) {
            return nestedResult
          }
        }
      }
      return { valid: true }
    }

    const rulesValidation = validateRules(data.rules)
    if (!rulesValidation.valid) {
      return rulesValidation
    }

    return { valid: true }
  }

  /**
   * 从JSON文件导入规则配置
   */
  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 检查文件类型
    if (!file.name.endsWith('.json')) {
      setImportError('请选择JSON文件')
      setImportSuccess(false)
      return
    }

    const reader = new FileReader()

    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        const parsedData = JSON.parse(content)

        // 验证规则配置
        const validation = validateRuleConfig(parsedData)
        if (!validation.valid) {
          setImportError(validation.error || '规则配置验证失败')
          setImportSuccess(false)
          return
        }

        // 导入成功
        onImport(parsedData as RuleConfig)
        setImportError(null)
        setImportSuccess(true)

        // 3秒后清除成功提示
        setTimeout(() => {
          setImportSuccess(false)
        }, 3000)

        console.log('规则配置已导入:', file.name)
      } catch (error) {
        console.error('导入失败:', error)
        setImportError('JSON解析失败: ' + (error as Error).message)
        setImportSuccess(false)
      }
    }

    reader.onerror = () => {
      setImportError('文件读取失败')
      setImportSuccess(false)
    }

    reader.readAsText(file)

    // 重置文件输入，允许重复导入同一文件
    event.target.value = ''
  }

  /**
   * 触发文件选择对话框
   */
  const triggerFileInput = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-3">
      {/* 操作按钮 */}
      <div className="flex gap-2">
        <Button
          onClick={handleExport}
          variant="outline"
          size="sm"
          className="flex-1"
        >
          <Download className="h-4 w-4 mr-2" />
          导出JSON
        </Button>

        <Button
          onClick={triggerFileInput}
          variant="outline"
          size="sm"
          className="flex-1"
        >
          <Upload className="h-4 w-4 mr-2" />
          导入JSON
        </Button>
      </div>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleImport}
        className="hidden"
      />

      {/* 错误提示 */}
      {importError && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="pt-4">
            <div className="flex items-start gap-2 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium">导入失败</div>
                <div className="text-xs mt-1">{importError}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 成功提示 */}
      {importSuccess && (
        <Card className="border-green-200 bg-green-50/50">
          <CardContent className="pt-4">
            <div className="flex items-start gap-2 text-sm text-green-700">
              <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium">导入成功</div>
                <div className="text-xs mt-1">规则配置已加载</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 格式说明 */}
      <Card className="bg-muted/50">
        <CardContent className="pt-4">
          <div className="flex items-start gap-2 text-xs text-muted-foreground">
            <FileJson className="h-3 w-3 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium">JSON格式说明</div>
              <div className="mt-1">
                导出的JSON格式与数据库存储格式一致，包含logic、rules和output三个主要字段。
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
