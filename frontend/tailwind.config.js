/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a'
        },
        secondary: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7c3aed',
          800: '#6b21a8',
          900: '#581c87'
        }
      },
      fontFamily: {
        // 使用本地离线字体，支持 Windows 和国产 Linux 系统
        // 主字体：思源黑体 CN（现代、专业的中文字体）
        // 备用：系统字体
        sans: [
          '"Source Han Sans CN"',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif'
        ],
        // 等宽字体：Cascadia Code（代码显示）
        mono: [
          '"Cascadia Code"',
          '"SF Mono"',
          'Monaco',
          'Consolas',
          '"Courier New"',
          'monospace'
        ]
      },
      borderRadius: {
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem'
      },
      boxShadow: {
        card: '0 2px 12px rgba(0, 0, 0, 0.1)'
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      }
    }
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        light: {
          'color-scheme': 'light',

          // 品牌核心色（饱和度略降）
          primary: 'oklch(0.55 0.18 250)', // 原 0.22→0.18
          secondary: 'oklch(0.60 0.20 295)', // 原 0.25→0.20
          accent: 'oklch(0.65 0.16 155)', // 原 0.20→0.16

          // 灰阶
          neutral: 'oklch(0.21 0.01 250)',
          'base-100': 'oklch(0.99 0 0)',
          'base-200': 'oklch(0.95 0 0)',
          'base-300': 'oklch(0.92 0 0)',

          // 状态色——整体饱和度下调
          info: 'oklch(0.65 0.12 240)', // 原 0.17→0.12
          success: 'oklch(0.65 0.12 155)', // 原 0.20→0.12
          warning: 'oklch(0.75 0.10  85)', // 原 0.15→0.10
          error: 'oklch(0.65 0.15  25)', // 原 0.25→0.15

          // 文字对比色
          'primary-content': 'oklch(0.99 0 0)',
          'secondary-content': 'oklch(0.99 0 0)',
          'accent-content': 'oklch(0.99 0 0)',
          'neutral-content': 'oklch(0.95 0 0)',
          'base-content': 'oklch(0.21 0.01 250)'
        }
      },
      {
        dark: {
          'color-scheme': 'dark',

          // 暗色品牌色（亮度稍提，饱和度降低）
          primary: 'oklch(0.72 0.18 250)', // 亮度↑ 色度↓
          secondary: 'oklch(0.72 0.20 295)',
          accent: 'oklch(0.76 0.16 155)',

          // 灰阶整体提亮
          neutral: 'oklch(0.92 0 0)',
          'base-100': 'oklch(0.18 0.01 250)', // 原 0.15→0.18
          'base-200': 'oklch(0.14 0.01 250)', // 原 0.11→0.14
          'base-300': 'oklch(0.10 0.01 250)', // 原 0.07→0.10

          // 暗色状态色（饱和度同步降低）
          info: 'oklch(0.72 0.12 240)',
          success: 'oklch(0.72 0.12 155)',
          warning: 'oklch(0.80 0.10  85)',
          error: 'oklch(0.72 0.15  25)',

          // 暗色对比色
          'primary-content': 'oklch(0.15 0 0)',
          'secondary-content': 'oklch(0.15 0 0)',
          'accent-content': 'oklch(0.15 0 0)',
          'neutral-content': 'oklch(0.15 0 0)',
          'base-content': 'oklch(0.92 0 0)'
        }
      }
    ],
    darkTheme: 'dark',
    base: true,
    styled: true,
    utils: true,
    prefix: '',
    logs: false,
    themeRoot: ':root'
  }
}
