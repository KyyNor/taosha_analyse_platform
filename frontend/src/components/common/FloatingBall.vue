<template>
  <div class="fixed bottom-6 left-6 z-50">
    <!-- 悬浮球 -->
    <button
      v-if="!isExpanded"
      class="w-14 h-14 bg-primary text-primary-content rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group hover:scale-110"
      @click="toggleExpand"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
        />
      </svg>
      <div class="absolute left-full ml-2 px-2 py-1 bg-base-300 text-base-content text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
        查询历史和收藏
      </div>
    </button>

    <!-- 缩小按钮（当侧边栏展开时显示） -->
    <button
      v-else
      class="w-10 h-10 bg-base-300 text-base-content rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center hover:scale-110"
      @click="toggleExpand"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  isExpanded: boolean
}

interface Emits {
  (e: 'toggle'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const toggleExpand = () => {
  emit('toggle')
}
</script>