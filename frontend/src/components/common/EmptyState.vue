<template>
  <div
    class="flex flex-col items-center justify-center p-8 text-center"
    :class="containerClass"
  >
    <!-- Icon -->
    <div
      class="mb-4"
      :class="iconContainerClass"
    >
      <component
        :is="iconComponent"
        class="w-12 h-12"
      />
    </div>

    <!-- Title -->
    <h3
      class="text-lg font-semibold mb-2"
      :class="titleClass"
    >
      {{ title }}
    </h3>

    <!-- Description -->
    <p
      class="text-sm text-base-content/60 mb-6 max-w-md"
      :class="descriptionClass"
    >
      {{ description }}
    </p>

    <!-- Action Buttons -->
    <div
      v-if="$slots.action || primaryAction"
      class="flex gap-3 flex-wrap justify-center"
    >
      <slot name="action">
        <button
          v-if="primaryAction"
          class="btn btn-primary"
          @click="primaryAction.handler"
        >
          {{ primaryAction.text }}
        </button>
        <button
          v-if="secondaryAction"
          class="btn btn-outline"
          @click="secondaryAction.handler"
        >
          {{ secondaryAction.text }}
        </button>
      </slot>
    </div>

    <!-- Additional Content -->
    <div
      v-if="$slots.default"
      class="mt-6"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Action {
  text: string
  handler: () => void
}

interface Props {
  type?: 'no-data' | 'no-results' | 'error' | 'network-error' | 'not-found' | 'custom'
  title?: string
  description?: string
  icon?: string
  size?: 'sm' | 'md' | 'lg'
  compact?: boolean
  className?: string
  primaryAction?: Action
  secondaryAction?: Action
}

const props = withDefaults(defineProps<Props>(), {
  type: 'no-data',
  size: 'md',
  compact: false,
  className: ''
})

// Default titles and descriptions by type
const defaultContent = {
  'no-data': {
    title: '暂无数据',
    description: '当前没有可显示的数据，请稍后再试或添加新数据。'
  },
  'no-results': {
    title: '没有找到结果',
    description: '根据您的搜索条件没有找到匹配的结果，请尝试调整搜索条件。'
  },
  'error': {
    title: '出错了',
    description: '系统遇到了一些问题，请刷新页面重试或联系技术支持。'
  },
  'network-error': {
    title: '网络连接失败',
    description: '无法连接到服务器，请检查网络连接后重试。'
  },
  'not-found': {
    title: '页面未找到',
    description: '您访问的页面不存在或已被移除。'
  },
  'custom': {
    title: '',
    description: ''
  }
}

// Get title and description
const title = computed(() => props.title || defaultContent[props.type].title)
const description = computed(() => props.description || defaultContent[props.type].description)

// Size classes
const sizeClasses = {
  sm: {
    container: 'p-4',
    icon: 'w-8 h-8',
    title: 'text-base',
    description: 'text-xs'
  },
  md: {
    container: 'p-8',
    icon: 'w-12 h-12',
    title: 'text-lg',
    description: 'text-sm'
  },
  lg: {
    container: 'p-12',
    icon: 'w-16 h-16',
    title: 'text-xl',
    description: 'text-base'
  }
}

// Icon components
const iconComponents = {
  'no-data': () => h('svg', {
    xmlns: 'http://www.w3.org/2000/svg',
    fill: 'none',
    viewBox: '0 0 24 24',
    stroke: 'currentColor'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
    })
  ]),
  'no-results': () => h('svg', {
    xmlns: 'http://www.w3.org/2000/svg',
    fill: 'none',
    viewBox: '0 0 24 24',
    stroke: 'currentColor'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
    })
  ]),
  'error': () => h('svg', {
    xmlns: 'http://www.w3.org/2000/svg',
    fill: 'none',
    viewBox: '0 0 24 24',
    stroke: 'currentColor'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    })
  ]),
  'network-error': () => h('svg', {
    xmlns: 'http://www.w3.org/2000/svg',
    fill: 'none',
    viewBox: '0 0 24 24',
    stroke: 'currentColor'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: 'M18.364 5.636l-12.728 12.728m0-12.728l12.728 12.728M9.172 9.172L4.343 4.343m6.829 6.829l-4.829 4.829m12.829-12.829l4.829 4.829M14.828 14.828l4.829 4.829M4.343 19.657l4.829-4.829'
    })
  ]),
  'not-found': () => h('svg', {
    xmlns: 'http://www.w3.org/2000/svg',
    fill: 'none',
    viewBox: '0 0 24 24',
    stroke: 'currentColor'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: 'M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    })
  ])
}

// Computed classes
const containerClass = computed(() => {
  const classes = [sizeClasses[props.size].container]

  if (props.compact) {
    classes.push('py-4')
  }

  if (props.className) {
    classes.push(props.className)
  }

  return classes.join(' ')
})

const iconContainerClass = computed(() => {
  return `text-base-content/40 ${sizeClasses[props.size].icon}`
})

const iconComponent = computed(() => {
  return iconComponents[props.type] || iconComponents['no-data']
})

const titleClass = computed(() => {
  return sizeClasses[props.size].title
})

const descriptionClass = computed(() => {
  return sizeClasses[props.size].description
})
</script>
