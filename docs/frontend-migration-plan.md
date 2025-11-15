# 淘沙分析平台前端迁移方案

## 项目概述

**迁移目标**：将淘沙分析平台前端从 Vue 3 + TypeScript + DaisyUI 迁移到 Next.js + React + TypeScript + shadcn/ui

**迁移范围**：
- ✅ **迁移内容**：元数据管理（表配置、关联配置、业务术语、提示词配置、数据主题）
- ✅ **重构内容**：Agent功能（使用 CopilotKit 组件）
- ❌ **不迁移**：淘沙查询、日志管理、我的收藏、系统设置、悬浮框

**源项目**：`frontend_bak/` (Vue 3 + TypeScript + DaisyUI)
**目标项目**：`frontend/` (Next.js + React + TypeScript + shadcn/ui)

## 一、可复用文件分析

### 1.1 完全复用的文件 ⭐⭐⭐⭐⭐

这些文件无需修改，可直接复制到新项目：

#### 类型定义文件
```
types/index.ts → frontend/types/index.ts
```
- 包含所有业务接口类型定义
- TypeScript 接口定义，框架无关
- 涵盖元数据、查询、Agent、用户界面等所有类型

#### API配置文件
```
config/api.ts → frontend/lib/config/api.ts
```
- API端点配置和辅助函数
- 只需修改环境变量获取方式（从 `import.meta.env` 改为 `process.env`）

### 1.2 部分改造后复用的文件 ⭐⭐⭐⭐

#### API服务层文件
```
services/api/metadataService.ts → frontend/lib/services/metadataService.ts
services/api/client.ts → frontend/lib/services/apiClient.ts
```

**改造要点**：
- 修改导入路径语法（`@/` → `@/` 或相对路径）
- 适配新的 HTTP 客户端（可继续使用 Axios 或改用 Fetch API）
- 环境变量获取方式调整

**示例改造**：
```typescript
// 原文件
import { api } from './client'
import { API_ENDPOINTS, buildApiUrl } from '@/config/api'

// 改造后
import { api } from './apiClient'
import { API_ENDPOINTS, buildApiUrl } from '@/lib/config/api'
```

## 二、需要重构的组件

### 2.1 元数据管理页面组件（Vue → React）

这些是核心业务组件，需要完整重写为 React 组件：

#### 表配置管理
```
views/metadata/TablesPage.vue → frontend/app/metadata/tables/page.tsx
```
**功能迁移要点**：
- 表格展示使用 shadcn/ui 的 `Table` 组件
- 分页使用 `use-pagination` hook
- 搜索防抖使用 `use-debounce` hook
- 模态框使用 `Dialog` 组件
- 表单使用 `react-hook-form` + `zod`

**Vue 原代码结构**：
```vue
<template>
  <div class="space-y-6">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4">
      <input v-model="filters.search" @input="debouncedSearch" />
      <button @click="openAddTable">添加表</button>
    </div>

    <!-- DataTable -->
    <DataTable :data="tables" :columns="tableColumns" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import metadataService from '@/services/api/metadataService'

const tables = ref([])
const loading = ref(false)

const loadTables = async () => {
  loading.value = true
  try {
    tables.value = await metadataService.getTables()
  } finally {
    loading.value = false
  }
}
</script>
```

**React 目标代码结构**：
```tsx
'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable } from '@/components/ui/data-table'
import { useTables, useCreateTable } from '@/hooks/use-metadata'
import { useMetadataStore } from '@/store/use-metadata-store'

export default function TablesPage() {
  // TanStack Query - 服务端状态管理
  const { data: tables, isLoading, error } = useTables()
  const createTableMutation = useCreateTable()

  // Zustand - 客户端状态管理
  const {
    searchQuery,
    setSearchQuery,
    editingTable,
    setEditingTable,
  } = useMetadataStore()

  const handleCreateTable = () => {
    setEditingTable({
      name: '',
      comment: '',
      remark: '',
      isAvailable: true,
      dataSource: '',
      updateMethod: ''
    } as TableMetadata)
  }

  const handleSearch = (query: string) => {
    setSearchQuery(query)
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <Input
          placeholder="搜索表名或注释..."
          value={searchQuery || ''}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-md"
        />
        <Button onClick={handleCreateTable}>
          添加表
        </Button>
      </div>

      <DataTable
        data={tables || []}
        columns={tableColumns}
        loading={isLoading}
        error={error?.message}
      />
    </div>
  )
}
```

#### 其他元数据页面组件
```
views/metadata/GlossaryPage.vue → frontend/app/metadata/glossary/page.tsx
views/metadata/RelationsPage.vue → frontend/app/metadata/relations/page.tsx
views/metadata/PromptTemplatesPage.vue → frontend/app/metadata/prompts/page.tsx
views/metadata/ThemesPage.vue → frontend/app/metadata/themes/page.tsx
```

### 2.2 通用组件重构

#### 数据表格组件
```
components/common/DataTable.vue → frontend/components/ui/data-table.tsx
```

**重构要点**：
- 使用 shadcn/ui 的 `Table` 组件作为基础
- 实现排序、搜索、分页功能
- 支持自定义列渲染
- TypeScript 类型安全

**功能特性保留**：
- ✅ 排序功能
- ✅ 搜索功能
- ✅ 分页功能
- ✅ 列显示/隐藏设置
- ✅ 行选择功能
- ✅ 自定义列渲染
- ✅ 空状态处理

#### 其他通用组件
```
components/common/LoadingSpinner.vue → frontend/components/ui/loading-spinner.tsx
```

## 三、状态管理迁移

### 3.1 从 Pinia 到 React 状态管理

**原 Pinia Stores**：
```
stores/app.ts → Zustand (全局应用状态)
stores/query.ts → TanStack Query (服务端状态)
stores/agentStore.ts → TanStack Query + Zustand
stores/theme.ts → Zustand (主题状态)
```

### 3.2 推荐的状态管理方案：Zustand + TanStack Query

**架构理念**：
- **Zustand**：管理客户端状态（UI状态、用户交互状态、临时数据）
- **TanStack Query**：管理服务端状态（API数据、缓存、同步）
- **React Hook Form**：管理表单状态（验证、提交、重置）

#### 1. 全局应用状态（使用 Zustand）

```typescript
// store/use-app-store.ts
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface AppState {
  // 主题相关
  theme: 'light' | 'dark'

  // UI状态
  sidebarOpen: boolean
  loading: boolean

  // 通知系统
  notifications: Notification[]

  // 用户信息
  user: User | null

  // 操作方法
  setTheme: (theme: 'light' | 'dark') => void
  toggleSidebar: () => void
  setLoading: (loading: boolean) => void
  addNotification: (notification: Notification) => void
  removeNotification: (id: string) => void
  setUser: (user: User | null) => void
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        theme: 'light',
        sidebarOpen: true,
        loading: false,
        notifications: [],
        user: null,

        setTheme: (theme) => set({ theme }),
        toggleSidebar: () => set((state) => ({
          sidebarOpen: !state.sidebarOpen
        })),
        setLoading: (loading) => set({ loading }),

        addNotification: (notification) => set((state) => ({
          notifications: [...state.notifications, notification]
        })),

        removeNotification: (id) => set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),

        setUser: (user) => set({ user }),
      }),
      {
        name: 'app-store',
        partialize: (state) => ({
          theme: state.theme,
          user: state.user
        }),
      }
    )
  )
)
```

#### 2. 元数据管理专用状态（使用 Zustand）

```typescript
// store/use-metadata-store.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { TableMetadata, GlossaryTerm, RelationConfig, DataTheme } from '@/types'

interface MetadataStore {
  // 当前选中的项目
  selectedTable: TableMetadata | null
  selectedGlossary: GlossaryTerm | null
  selectedRelation: RelationConfig | null
  selectedTheme: DataTheme | null

  // 编辑状态
  editingTable: TableMetadata | null
  editingGlossary: GlossaryTerm | null
  editingRelation: RelationConfig | null
  editingTheme: DataTheme | null

  // UI状态
  activeTab: 'tables' | 'glossary' | 'relations' | 'prompts' | 'themes'
  searchQuery: string
  filters: {
    type?: string
    isAvailable?: boolean
    dataSource?: string
  }

  // 操作方法
  setSelectedTable: (table: TableMetadata | null) => void
  setEditingTable: (table: TableMetadata | null) => void
  setActiveTab: (tab: string) => void
  setSearchQuery: (query: string) => void
  setFilters: (filters: Partial<MetadataStore['filters']>) => void
  clearSelections: () => void
}

export const useMetadataStore = create<MetadataStore>()(
  devtools(
    (set) => ({
      selectedTable: null,
      selectedGlossary: null,
      selectedRelation: null,
      selectedTheme: null,

      editingTable: null,
      editingGlossary: null,
      editingRelation: null,
      editingTheme: null,

      activeTab: 'tables',
      searchQuery: '',
      filters: {},

      setSelectedTable: (selectedTable) => set({ selectedTable }),
      setEditingTable: (editingTable) => set({ editingTable }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setSearchQuery: (searchQuery) => set({ searchQuery }),
      setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters }
      })),
      clearSelections: () => set({
        selectedTable: null,
        selectedGlossary: null,
        selectedRelation: null,
        selectedTheme: null,
        editingTable: null,
        editingGlossary: null,
        editingRelation: null,
        editingTheme: null,
      }),
    }),
    { name: 'metadata-store' }
  )
)
```

#### 3. 服务端状态管理（使用 TanStack Query）

```typescript
// hooks/use-metadata.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMetadataStore } from '@/store/use-metadata-store'
import { useAppStore } from '@/store/use-app-store'
import metadataService from '@/lib/services/metadataService'

// 表数据查询
export function useTables() {
  const searchQuery = useMetadataStore(state => state.searchQuery)
  const filters = useMetadataStore(state => state.filters)

  return useQuery({
    queryKey: ['tables', searchQuery, filters],
    queryFn: () => metadataService.getTables(true, filters.isAvailable, searchQuery),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    select: (data) => data.sort((a, b) => a.name.localeCompare(b.name)),
  })
}

// 创建表
export function useCreateTable() {
  const queryClient = useQueryClient()
  const setEditingTable = useMetadataStore(state => state.setEditingTable)
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.createTable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      setEditingTable(null)
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '创建成功',
        message: '表配置已创建'
      })
    },
    onError: (error) => {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        title: '创建失败',
        message: error.message
      })
    }
  })
}

// 业务术语查询
export function useGlossaryTerms() {
  const searchQuery = useMetadataStore(state => state.searchQuery)
  const filters = useMetadataStore(state => state.filters)

  return useQuery({
    queryKey: ['glossary', searchQuery, filters],
    queryFn: () => {
      if (filters.type) {
        return metadataService.getGlossaryTermsByType(filters.type)
      }
      return metadataService.getGlossaryTerms()
    },
    staleTime: 5 * 60 * 1000,
  })
}

// 批量更新表和字段
export function useBatchUpdate() {
  const queryClient = useQueryClient()
  const addNotification = useAppStore(state => state.addNotification)

  return useMutation({
    mutationFn: metadataService.batchUpdateTableAndColumns,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
      addNotification({
        id: Date.now().toString(),
        type: 'success',
        title: '批量更新成功',
        message: `成功更新 ${data.success_count} 项，失败 ${data.error_count} 项`
      })
    },
  })
}
```

#### 4. 表单状态管理（使用 react-hook-form + zod）

```typescript
// hooks/use-table-form.ts
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { TableFormData } from '@/types'

const tableSchema = z.object({
  name: z.string().min(1, '表名不能为空'),
  comment: z.string().optional(),
  remark: z.string().optional(),
  isAvailable: z.boolean(),
  dataSource: z.string().optional(),
  updateMethod: z.string().optional(),
})

export function useTableForm(defaultValues?: Partial<TableFormData>) {
  const editingTable = useMetadataStore(state => state.editingTable)

  return useForm<TableFormData>({
    resolver: zodResolver(tableSchema),
    defaultValues: {
      name: '',
      comment: '',
      remark: '',
      isAvailable: true,
      dataSource: '',
      updateMethod: '',
      ...editingTable,
      ...defaultValues,
    },
  })
}

// hooks/use-glossary-form.ts
export function useGlossaryForm() {
  const editingGlossary = useMetadataStore(state => state.editingGlossary)

  return useForm<GlossaryFormData>({
    resolver: zodResolver(glossarySchema),
    defaultValues: {
      name: '',
      type: 'concept',
      content: {},
      creator: '',
      ...editingGlossary,
    },
  })
}
```

#### 5. 状态管理在组件中的使用示例

```typescript
// app/metadata/tables/page.tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable } from '@/components/ui/data-table'
import { useTables, useCreateTable } from '@/hooks/use-metadata'
import { useMetadataStore } from '@/store/use-metadata-store'
import { useTableForm } from '@/hooks/use-table-form'

export default function TablesPage() {
  const { data: tables, isLoading, error } = useTables()
  const createTableMutation = useCreateTable()

  const {
    searchQuery,
    setSearchQuery,
    editingTable,
    setEditingTable,
    activeTab,
    setActiveTab
  } = useMetadataStore()

  const form = useTableForm()

  const handleCreateTable = async (data: TableFormData) => {
    createTableMutation.mutate(data)
  }

  const handleSearch = (query: string) => {
    setSearchQuery(query)
  }

  return (
    <div className="space-y-6">
      {/* 搜索和操作区域 */}
      <div className="flex gap-4 items-center">
        <Input
          placeholder="搜索表名或注释..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-md"
        />
        <Button onClick={() => setEditingTable({} as TableMetadata)}>
          添加表
        </Button>
      </div>

      {/* 数据表格 */}
      <DataTable
        data={tables || []}
        columns={tableColumns}
        loading={isLoading}
        error={error?.message}
      />
    </div>
  )
}
```

### 3.3 状态管理架构优势

#### Zustand 优势：
- **极简API**：学习成本低，代码简洁
- **性能优秀**：选择性订阅，避免不必要的重渲染
- **TypeScript友好**：完整的类型推断
- **无Provider依赖**：直接在组件中使用
- **轻量级**：包体积仅 2.6kb
- **中间件支持**：devtools、persist、immer等

#### TanStack Query 优势：
- **专注服务端状态**：API数据获取、缓存、同步
- **自动重新获取**：窗口聚焦、网络重连、数据过期
- **乐观更新**：提升用户体验
- **分页和无限滚动**：内置支持
- **错误处理**：统一的错误处理和重试机制
- **开发者工具**：强大的调试工具

#### 组合优势：
- **职责清晰**：客户端状态 vs 服务端状态
- **性能优化**：最小化重渲染，智能缓存
- **开发效率**：减少样板代码，专注业务逻辑
- **可维护性**：状态管理逻辑集中，易于测试和调试

## 四、UI组件库迁移

### 4.1 从 DaisyUI 到 shadcn/ui

**组件对应关系**：

| DaisyUI 组件 | shadcn/ui 组件 | 说明 |
|-------------|---------------|------|
| `btn` | `Button` | 按钮组件 |
| `input` | `Input` | 输入框组件 |
| `select` | `Select` | 选择器组件 |
| `modal` | `Dialog` | 对话框组件 |
| `dropdown` | `DropdownMenu` | 下拉菜单组件 |
| `card` | `Card` | 卡片组件 |
| `badge` | `Badge` | 徽章组件 |
| `loading` | `LoadingSpinner` | 加载指示器 |
| `table` | `Table` | 表格组件 |

### 4.2 样式系统迁移

#### DaisyUI → Tailwind CSS + shadcn/ui
```css
/* DaisyUI 样式 */
<div class="btn btn-primary">按钮</div>
<div class="modal modal-open">
  <div class="modal-box">内容</div>
</div>

/* shadcn/ui 样式 */
<Button>按钮</Button>
<Dialog open>
  <DialogContent>内容</DialogContent>
</Dialog>
```

#### 主题配置
```typescript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
      }
    }
  }
}
```

## 五、Agent 功能重构

### 5.1 使用 CopilotKit 重构 Agent

**原 Agent 组件**：
```
views/AgentPage.vue + components/agent/ → 使用 CopilotChat 组件
```

**新 Agent 实现**：
```tsx
// app/agent/page.tsx
'use client'

import { CopilotChat } from "@copilotkit/react-ui"

export default function AgentPage() {
  return (
    <div className="h-screen flex flex-col">
      <CopilotChat
        instructions="You are assisting the user as best as you can. Answer in the best way possible given the data you have."
        labels={{
          title: "淘沙助手",
          initial: "👋 您好！我是淘沙数据分析助手，请问有什么可以帮助您的吗？",
        }}
        className="flex-1"
      />
    </div>
  )
}
```

### 5.2 集成现有 API 服务

```typescript
// lib/copilotkit/prompts.ts
export const TAOSHA_SYSTEM_PROMPT = `你是淘沙分析平台的AI助手，专门帮助用户进行数据分析和查询。

你的职责包括：
1. 帮助用户理解数据结构和表关系
2. 协助编写自然语言查询
3. 解释查询结果和数据洞察
4. 提供数据分析建议

当前可用的数据表：
{{#each tables}}
- {{name}}: {{comment}}
{{/each}}
`
```

## 六、路由系统迁移

### 6.1 从 Vue Router 到 Next.js App Router

**原路由配置**：
```typescript
// router/index.ts
const routes = [
  { path: '/metadata/tables', component: TablesPage },
  { path: '/metadata/glossary', component: GlossaryPage },
  { path: '/metadata/relations', component: RelationsPage },
  { path: '/metadata/prompts', component: PromptTemplatesPage },
  { path: '/metadata/themes', component: ThemesPage },
  { path: '/agent', component: AgentPage }
]
```

**Next.js App Router**：
```
app/
├── metadata/
│   ├── tables/
│   │   └── page.tsx
│   ├── glossary/
│   │   └── page.tsx
│   ├── relations/
│   │   └── page.tsx
│   ├── prompts/
│   │   └── page.tsx
│   └── themes/
│       └── page.tsx
├── agent/
│   └── page.tsx
├── layout.tsx
└── page.tsx
```

### 6.2 导航组件

```tsx
// components/layout/sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navigation = [
  { name: 'Agent助手', href: '/agent' },
  { name: '表配置', href: '/metadata/tables' },
  { name: '业务术语', href: '/metadata/glossary' },
  { name: '关联配置', href: '/metadata/relations' },
  { name: '提示词配置', href: '/metadata/prompts' },
  { name: '数据主题', href: '/metadata/themes' }
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <nav className="space-y-1">
      {navigation.map((item) => (
        <Link
          key={item.name}
          href={item.href}
          className={`${
            pathname === item.href
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent'
          }`}
        >
          {item.name}
        </Link>
      ))}
    </nav>
  )
}
```

## 七、表单处理迁移

### 7.1 从 Vue 表单到 React Hook Form

**原表单处理**：
```vue
<script setup lang="ts">
import { ref, reactive } from 'vue'

const form = reactive({
  name: '',
  comment: '',
  remark: '',
  isAvailable: true
})

const submitForm = async () => {
  try {
    await metadataService.createTable(form)
    // 关闭模态框，刷新列表
  } catch (error) {
    // 错误处理
  }
}
</script>
```

**React Hook Form 迁移**：
```tsx
// hooks/use-table-form.ts
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { tableSchema } from '@/schemas/table'
import { useMetadataStore } from '@/store/use-metadata-store'
import { useCreateTable, useUpdateTable } from '@/hooks/use-metadata'

export function useTableForm() {
  const editingTable = useMetadataStore(state => state.editingTable)
  const setEditingTable = useMetadataStore(state => state.setEditingTable)
  const createTableMutation = useCreateTable()
  const updateTableMutation = useUpdateTable()

  const form = useForm<TableFormData>({
    resolver: zodResolver(tableSchema),
    defaultValues: {
      name: '',
      comment: '',
      remark: '',
      isAvailable: true,
      dataSource: '',
      updateMethod: '',
      ...editingTable,
    },
  })

  const handleSubmit = form.handleSubmit(async (data) => {
    try {
      if (editingTable?.id) {
        // 更新现有表
        await updateTableMutation.mutateAsync({
          id: editingTable.id,
          data
        })
      } else {
        // 创建新表
        await createTableMutation.mutateAsync(data)
      }
      setEditingTable(null)
      form.reset()
    } catch (error) {
      // 错误处理在 mutation 中统一处理
    }
  })

  const handleCancel = () => {
    setEditingTable(null)
    form.reset()
  }

  return { form, handleSubmit, handleCancel, isEditing: !!editingTable?.id }
}
```

## 八、错误处理和加载状态

### 8.1 统一的错误处理

```typescript
// hooks/use-error-boundary.ts
import { useState } from 'react'

export function useErrorBoundary() {
  const [error, setError] = useState<Error | null>(null)

  const resetError = () => setError(null)

  const captureError = (error: Error) => {
    console.error('Application error:', error)
    setError(error)
  }

  return { error, captureError, resetError }
}
```

### 8.2 全局加载状态

```typescript
// components/ui/loading.tsx
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <Loader2
      className={`animate-spin ${sizeClasses[size]} ${className}`}
    />
  )
}
```

## 九、实施计划

### 9.1 第一阶段：基础设施搭建（1-2天）

1. **项目初始化**
   ```bash
   npx create-next-app@latest frontend --typescript --tailwind --eslint
   npx shadcn-ui@latest init
   ```

2. **安装依赖**
   ```bash
   npm install @copilotkit/react-ui @copilotkit/react-core
   npm install react-hook-form @hookform/resolvers zod
   npm install @tanstack/react-query axios
   npm install zustand
   npm install lucide-react
   ```

3. **复制可复用文件**
   - `types/index.ts`
   - `utils/` 目录
   - `config/api.ts`

### 9.2 第二阶段：核心组件迁移（3-5天）

1. **API服务层改造**
   - 修改 `metadataService.ts`
   - 创建 `apiClient.ts`
   - 配置环境变量

2. **通用组件开发**
   - `DataTable` 组件
   - `LoadingSpinner` 组件
   - `EmptyState` 组件

3. **布局系统**
   - `Layout` 组件
   - `Sidebar` 导航
   - 主题切换

### 9.3 第三阶段：元数据页面迁移（5-7天）

1. **表配置管理页面**（优先级最高）
2. **业务术语管理页面**
3. **关联配置管理页面**
4. **提示词配置页面**
5. **数据主题管理页面**

### 9.4 第四阶段：Agent功能集成（2-3天）

1. **CopilotKit 集成**
2. **Agent 页面开发**
3. **自定义提示词配置**

### 9.5 第五阶段：测试和优化（2-3天）

1. **功能测试**
2. **性能优化**
3. **用户体验优化**
4. **文档编写**

## 十、风险评估和缓解措施

### 10.1 主要风险

1. **组件复杂度风险**
   - 某些 Vue 组件逻辑复杂，直接转换困难
   - **缓解措施**：先实现核心功能，复杂功能后续迭代

2. **样式一致性风险**
   - DaisyUI 和 shadcn/ui 的设计语言差异
   - **缓解措施**：制定统一的 Design System，渐进式迁移

3. **状态管理复杂度风险**
   - Pinia 到 React 状态管理的思维转换
   - **缓解措施**：使用 React Query 管理服务端状态，简化本地状态管理

4. **时间延期风险**
   - 功能迁移工作量可能超出预期
   - **缓解措施**：分阶段交付，核心功能优先

### 10.2 技术选型备份方案

1. **UI 组件库**：备选 Ant Design、Material-UI
2. **状态管理**：备选 Redux Toolkit、Zustand
3. **表单处理**：备选 Formik + Yup
4. **HTTP 客户端**：备选 Fetch API、ky

## 十一、总结

### 11.1 迁移优势

1. **技术栈统一**：Next.js 提供更好的全栈开发体验
2. **SEO 友好**：SSR/SSG 提升搜索引擎优化
3. **性能提升**：React 18 + Next.js 性能优化
4. **生态丰富**：shadcn/ui + CopilotKit 现代化组件生态
5. **开发体验**：TypeScript + React DevTools 更好的开发体验

### 11.2 预期收益

- **代码复用率**：约 70%（类型定义 100%，工具函数 100%，API 服务 90%）
- **开发效率**：提升 30%（现代化工具链）
- **用户体验**：提升 40%（性能优化 + 现代化 UI）
- **维护成本**：降低 25%（统一技术栈）

### 11.3 成功指标

1. **功能完整性**：100% 核心功能迁移完成
2. **性能指标**：页面加载时间 < 2s，交互响应 < 100ms
3. **代码质量**：TypeScript 覆盖率 > 95%，ESLint 零警告
4. **用户体验**：用户满意度 > 85%

本迁移方案基于对现有 Vue 项目的深入分析，采用渐进式迁移策略，最大化代码复用，确保业务连续性的同时实现技术栈的现代化升级。