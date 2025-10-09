<template>
  <div
    class="flex items-center justify-center"
    :class="[containerClass, sizeClasses[size]]"
  >
    <span
      class="loading loading-spinner"
      :class="spinnerClasses"
    />
    <span
      v-if="showText"
      class="ml-2"
      :class="textClasses"
    >{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  text?: string
  showText?: boolean
  color?: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'error' | 'info'
  overlay?: boolean
  fullHeight?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  text: '加载中...',
  showText: true,
  color: 'primary',
  overlay: false,
  fullHeight: false,
  className: ''
})

// Size classes
const sizeClasses = {
  xs: 'text-xs',
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-xl'
}

// Spinner size classes
const spinnerSizeClasses = {
  xs: 'loading-xs',
  sm: 'loading-sm',
  md: 'loading-md',
  lg: 'loading-lg',
  xl: 'loading-lg'
}

// Container classes
const containerClass = computed(() => {
  const classes = []

  if (props.overlay) {
    classes.push('fixed inset-0 bg-black/20 backdrop-blur-sm z-50')
    classes.push('bg-base-100 p-6 rounded-lg shadow-xl')
  }

  if (props.fullHeight && !props.overlay) {
    classes.push('min-h-96')
  }

  if (props.className) {
    classes.push(props.className)
  }

  return classes.join(' ')
})

// Spinner classes
const spinnerClasses = computed(() => {
  const classes = [spinnerSizeClasses[props.size]]

  if (props.color !== 'primary') {
    classes.push(`text-${props.color}`)
  }

  return classes.join(' ')
})

// Text classes
const textClasses = computed(() => {
  const classes = ['font-medium']

  if (props.size === 'xs' || props.size === 'sm') {
    classes.push('text-xs')
  } else if (props.size === 'xl') {
    classes.push('text-lg')
  }

  return classes.join(' ')
})
</script>
