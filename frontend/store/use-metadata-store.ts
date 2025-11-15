import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { TableMetadata, GlossaryTerm, RelationConfig, DataTheme } from '@/types/index'

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
  setSelectedGlossary: (glossary: GlossaryTerm | null) => void
  setEditingGlossary: (glossary: GlossaryTerm | null) => void
  setSelectedRelation: (relation: RelationConfig | null) => void
  setEditingRelation: (relation: RelationConfig | null) => void
  setSelectedTheme: (theme: DataTheme | null) => void
  setEditingTheme: (theme: DataTheme | null) => void
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
      setSelectedGlossary: (selectedGlossary) => set({ selectedGlossary }),
      setEditingGlossary: (editingGlossary) => set({ editingGlossary }),
      setSelectedRelation: (selectedRelation) => set({ selectedRelation }),
      setEditingRelation: (editingRelation) => set({ editingRelation }),
      setSelectedTheme: (selectedTheme) => set({ selectedTheme }),
      setEditingTheme: (editingTheme) => set({ editingTheme }),
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