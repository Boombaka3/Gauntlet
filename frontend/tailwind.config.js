// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gauntlet: {
          bg:      '#0A0A0F',
          surface: '#111118',
          border:  '#1E1E2E',
          accent:  '#6366F1',
          success: '#10B981',
          warning: '#F59E0B',
          danger:  '#EF4444',
          muted:   '#64748B',
          text:    '#E2E8F0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
