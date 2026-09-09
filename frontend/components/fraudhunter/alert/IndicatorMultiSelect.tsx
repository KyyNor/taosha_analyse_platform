'use client'

/**
 * 指标多选组件
 *
 * 功能：
 * - 从指标列表中选择多个指标（值为 indicator_code，选择顺序即保存顺序）
 * - 默认只列在线指标，可切换显示全部状态
 * - 支持搜索（名称/编码）、全选/全不选、已选计数
 *
 * 数据获取：默认内部加载 indicatorService.list({ query_type: 'all' })；
 * 父组件已持有指标列表时可通过 indicators 属性传入避免重复请求。
 */

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Search, ChevronDown, Check } from 'lucide-react'
import { useState, useEffect, useMemo } from 'react'
import { indicatorService } from '@/lib/services/fraudhunterService'

// 指标选项的最小结构（与 indicatorService.list 返回项兼容）；
// service 层 Indicator 的 indicator_type 是 string，故不复用 rule 层窄类型
export interface IndicatorOption {
  indicator_code: string
  indicator_name: string
  indicator_type: string // offline/realtime
  status?: string
}

export function getIndicatorOptionDisplayName(indicator: IndicatorOption): string {
  return indicator.indicator_type === 'realtime'
    ? `[实时]${indicator.indicator_name}`
    : indicator.indicator_name
}

interface IndicatorMultiSelectProps {
  selectedCodes: string[]
  onChange: (codes: string[]) => void
  indicators?: IndicatorOption[]
  placeholder?: string
  className?: string
}

export function IndicatorMultiSelect({
  selectedCodes,
  onChange,
  indicators,
  placeholder = '选择指标',
  className = ''
}: IndicatorMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [allIndicators, setAllIndicators] = useState<IndicatorOption[]>(indicators || [])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [showAllStatus, setShowAllStatus] = useState(false)

  // 父组件未传入指标列表时自行加载
  useEffect(() => {
    if (indicators) {
      setAllIndicators(indicators)
      return
    }
    const loadIndicators = async () => {
      setLoading(true)
      try {
        const response = await indicatorService.list({ query_type: 'all' })
        setAllIndicators(response.items || [])
      } catch (error) {
        console.error('加载指标列表失败:', error)
      } finally {
        setLoading(false)
      }
    }
    loadIndicators()
  }, [indicators])

  // 默认只显示在线指标，勾选"显示全部状态"后显示全部
  const visibleIndicators = useMemo(() => {
    if (showAllStatus) return allIndicators
    return allIndicators.filter(i => !i.status || i.status === 'online')
  }, [allIndicators, showAllStatus])

  const filteredIndicators = useMemo(() => {
    if (!search.trim()) return visibleIndicators
    const kw = search.toLowerCase()
    return visibleIndicators.filter(
      (i) =>
        i.indicator_name.toLowerCase().includes(kw) ||
        i.indicator_code.toLowerCase().includes(kw)
    )
  }, [visibleIndicators, search])

  const isAllSelected =
    visibleIndicators.length > 0 &&
    visibleIndicators.every(i => selectedCodes.includes(i.indicator_code))

  const toggleOpen = (next: boolean) => {
    setOpen(next)
    if (next) setSearch('')
  }

  const toggleIndicator = (code: string) => {
    if (selectedCodes.includes(code)) {
      onChange(selectedCodes.filter(c => c !== code))
    } else {
      onChange([...selectedCodes, code])
    }
  }

  const selectAll = () => {
    // 追加当前可见但未选中的编码，保留已有选择顺序
    const additions = visibleIndicators
      .map(i => i.indicator_code)
      .filter(c => !selectedCodes.includes(c))
    onChange([...selectedCodes, ...additions])
  }

  const deselectVisible = () => {
    const visibleCodes = new Set(visibleIndicators.map(i => i.indicator_code))
    onChange(selectedCodes.filter(c => !visibleCodes.has(c)))
  }

  const getSummary = () => {
    if (selectedCodes.length === 0) return placeholder
    return `已选 ${selectedCodes.length} 个指标`
  }

  return (
    <Popover open={open} onOpenChange={toggleOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={`w-[280px] justify-between ${className}`}
        >
          <span className="truncate">{getSummary()}</span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[340px] p-0" align="start">
        {/* 搜索框 */}
        <div className="px-3 py-2 border-b">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="搜索指标名称/编码…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
              onKeyDown={(e) => e.key === 'Enter' && e.stopPropagation()}
            />
          </div>
        </div>
        {/* 全选/计数/状态过滤 */}
        <div className="flex items-center border-b px-3 py-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={isAllSelected ? deselectVisible : selectAll}
          >
            {isAllSelected ? '全不选' : '全选'}
          </Button>
          {selectedCodes.length > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {selectedCodes.length}
            </Badge>
          )}
        </div>
        <div className="flex items-center border-b px-3 py-1.5">
          <Checkbox
            id="indicator-show-all-status"
            checked={showAllStatus}
            onCheckedChange={(checked) => setShowAllStatus(checked === true)}
          />
          <label
            htmlFor="indicator-show-all-status"
            className="ml-2 text-xs text-muted-foreground cursor-pointer select-none"
          >
            显示全部状态（含非在线）
          </label>
        </div>
        <ScrollArea className="h-[300px]">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              加载中...
            </div>
          ) : filteredIndicators.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              {search ? '无匹配指标' : '暂无指标'}
            </div>
          ) : (
            <div className="p-2">
              {filteredIndicators.map((indicator) => {
                const isSelected = selectedCodes.includes(indicator.indicator_code)
                return (
                  <div
                    key={indicator.indicator_code}
                    className="flex items-center gap-2 rounded-sm px-2 py-1.5 hover:bg-accent cursor-pointer"
                    onClick={() => toggleIndicator(indicator.indicator_code)}
                  >
                    <Checkbox
                      checked={isSelected}
                      onChange={() => {}}
                    />
                    <span className="flex-1 text-sm truncate">
                      {getIndicatorOptionDisplayName(indicator)}
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({indicator.indicator_code})
                      </span>
                    </span>
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
