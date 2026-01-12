'use client'

/**
 * 模型多选组件
 *
 * 功能：
 * - 支持从模型列表中选择多个模型
 * - 支持全选/全不选
 * - 显示已选择的模型数量
 */

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChevronDown, Check } from 'lucide-react'
import { useState, useEffect } from 'react'
import { riskControlModelService } from '@/lib/services/fraudhunter/riskControlModelService'
import type { RiskControlModel } from '@/types/fraudhunter/risk-control-model'

interface ModelMultiSelectProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
  placeholder?: string
  className?: string
}

export function ModelMultiSelect({
  selectedIds,
  onChange,
  placeholder = '选择模型',
  className = ''
}: ModelMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [models, setModels] = useState<RiskControlModel[]>([])
  const [loading, setLoading] = useState(false)

  // 加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      setLoading(true)
      try {
        const response = await riskControlModelService.list({
          page: 1,
          page_size: 1000,
          status: 'online' // 只显示在线模型
        })
        setModels(response.items || [])
      } catch (error) {
        console.error('加载模型列表失败:', error)
      } finally {
        setLoading(false)
      }
    }
    loadModels()
  }, [])

  // 切换模型选择
  const toggleModel = (modelId: number) => {
    if (selectedIds.includes(modelId)) {
      onChange(selectedIds.filter(id => id !== modelId))
    } else {
      onChange([...selectedIds, modelId])
    }
  }

  // 全选
  const selectAll = () => {
    const allIds = models.map(m => m.id)
    onChange(allIds)
  }

  // 全不选
  const deselectAll = () => {
    onChange([])
  }

  // 是否全部选中
  const isAllSelected = models.length > 0 && selectedIds.length === models.length

  // 获取选中的模型名称
  const getSelectedNames = () => {
    if (selectedIds.length === 0) return placeholder
    if (selectedIds.length === models.length) return `全部模型 (${selectedIds.length})`
    return `已选 ${selectedIds.length} 个模型`
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={`w-[280px] justify-between ${className}`}
        >
          <span className="truncate">{getSelectedNames()}</span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[280px] p-0" align="start">
        <div className="flex items-center border-b px-3 py-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={isAllSelected ? deselectAll : selectAll}
          >
            {isAllSelected ? '全不选' : '全选'}
          </Button>
          {selectedIds.length > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {selectedIds.length}
            </Badge>
          )}
        </div>
        <ScrollArea className="h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              加载中...
            </div>
          ) : models.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              暂无模型
            </div>
          ) : (
            <div className="p-2">
              {models.map((model) => {
                const isSelected = selectedIds.includes(model.id)
                return (
                  <div
                    key={model.id}
                    className="flex items-center gap-2 rounded-sm px-2 py-1.5 hover:bg-accent cursor-pointer"
                    onClick={() => toggleModel(model.id)}
                  >
                    <Checkbox
                      checked={isSelected}
                      onChange={() => {}}
                    />
                    <span className="flex-1 text-sm truncate">{model.model_name}</span>
                    {isSelected && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}
