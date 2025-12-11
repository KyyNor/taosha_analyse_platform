'use client'

/**
 * 指标选择下拉框组件（支持搜索）
 *
 * 功能：
 * - 支持模糊搜索指标编码和名称
 * - 显示指标类型标签
 * - 支持键盘导航
 */

import { useState, useEffect, useRef } from 'react'
import { Check, ChevronsUpDown, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Indicator } from '@/types/fraudhunter/rule'
import { getIndicatorDisplayName } from '@/types/fraudhunter/rule'

interface IndicatorComboboxProps {
  indicators: Indicator[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  filterFn?: (indicator: Indicator) => boolean
}

export function IndicatorCombobox({
  indicators,
  value,
  onChange,
  placeholder = "选择指标",
  className,
  filterFn
}: IndicatorComboboxProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const selectedItemRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // 筛选指标列表
  const filteredIndicators = filterFn
    ? indicators.filter(filterFn)
    : indicators

  // 根据搜索查询筛选
  const searchedIndicators = filteredIndicators.filter(indicator => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    const code = indicator.indicator_code.toLowerCase()
    const name = indicator.indicator_name.toLowerCase()
    return code.includes(query) || name.includes(query)
  })

  // 获取当前选中的指标
  const selectedIndicator = indicators.find(
    ind => ind.indicator_code === value
  )

  // 当下拉框打开时，滚动到选中的项
  useEffect(() => {
    if (open && selectedItemRef.current && scrollContainerRef.current) {
      // 延迟滚动，确保DOM已渲染
      setTimeout(() => {
        if (selectedItemRef.current && scrollContainerRef.current) {
          const container = scrollContainerRef.current
          const item = selectedItemRef.current

          // 计算需要滚动的位置，使选中项位于容器中间
          const containerHeight = container.clientHeight
          const itemTop = item.offsetTop
          const itemHeight = item.clientHeight
          const scrollTop = itemTop - (containerHeight / 2) + (itemHeight / 2)

          container.scrollTop = Math.max(0, scrollTop)
        }
      }, 0)
    }
  }, [open])

  // 获取指标类型的颜色
  const getIndicatorTypeVariant = (type?: string) => {
    switch (type) {
      case 'realtime':
        return 'default'
      case 'offline':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  // 获取指标类型的标签文本
  const getIndicatorTypeLabel = (type?: string) => {
    switch (type) {
      case 'realtime':
        return '实时'
      case 'offline':
        return '离线'
      default:
        return '未知'
    }
  }

  return (
    <TooltipProvider>
      <Popover open={open} onOpenChange={setOpen}>
        <Tooltip>
          <TooltipTrigger asChild>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className={cn("justify-between h-8", className)}
              >
                {selectedIndicator ? (
                  <div className="flex items-center gap-1.5 flex-1 overflow-hidden">
                    <span className="truncate">
                      {getIndicatorDisplayName(selectedIndicator)}
                    </span>
                    {selectedIndicator.indicator_type && (
                      <Badge
                        variant={getIndicatorTypeVariant(selectedIndicator.indicator_type)}
                        className="text-[10px] px-1 py-0 h-4 flex-shrink-0"
                      >
                        {getIndicatorTypeLabel(selectedIndicator.indicator_type)}
                      </Badge>
                    )}
                  </div>
                ) : (
                  <span className="text-muted-foreground">{placeholder}</span>
                )}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
          </TooltipTrigger>
          {selectedIndicator && (
            <TooltipContent>
              <p>{selectedIndicator.indicator_name}</p>
            </TooltipContent>
          )}
        </Tooltip>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command shouldFilter={false}>
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <input
              placeholder="搜索指标编码或名称..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <CommandEmpty>未找到匹配的指标</CommandEmpty>
          <CommandGroup ref={scrollContainerRef} className="max-h-[300px] overflow-y-auto">
            {searchedIndicators.map((indicator) => (
              <CommandItem
                key={indicator.indicator_code}
                value={indicator.indicator_code}
                ref={value === indicator.indicator_code ? selectedItemRef : null}
                onSelect={() => {
                  onChange(indicator.indicator_code)
                  setOpen(false)
                  setSearchQuery('')
                }}
                className="flex items-center justify-between gap-2 py-2"
              >
                <div className="flex items-center gap-2 flex-1 overflow-hidden">
                  <Check
                    className={cn(
                      "h-4 w-4 flex-shrink-0",
                      value === indicator.indicator_code
                        ? "opacity-100"
                        : "opacity-0"
                    )}
                  />
                  <div className="flex flex-col flex-1 overflow-hidden">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">
                        {indicator.indicator_name}
                      </span>
                      {indicator.indicator_type && (
                        <Badge
                          variant={getIndicatorTypeVariant(indicator.indicator_type)}
                          className="text-[10px] px-1 py-0 h-4 flex-shrink-0"
                        >
                          {getIndicatorTypeLabel(indicator.indicator_type)}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="truncate">{indicator.indicator_code}</span>
                      <span>•</span>
                      <span>{indicator.data_type}</span>
                      {indicator.object_type && (
                        <>
                          <span>•</span>
                          <span>{indicator.object_type}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
    </TooltipProvider>
  )
}
