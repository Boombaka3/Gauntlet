// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gauntlet: {
          bg:           '#010102',
          surface:      '#0f1011',
          surface2:     '#141516',
          surface3:     '#18191a',
          border:       '#23252a',
          borderStrong: '#34343a',
          accent:       '#5e6ad2',
          accentHover:  '#828fff',
          success:      '#27a644',
          warning:      '#F59E0B',
          danger:       '#EF4444',
          text:         '#f7f8f8',
          muted:        '#d0d6e0',
          subtle:       '#8a8f98',
          tertiary:     '#62666d',
        },
        linear: {
          canvas:              '#010102',
          surface1:            '#0f1011',
          surface2:            '#141516',
          surface3:            '#18191a',
          surface4:            '#191a1b',
          hairline:            '#23252a',
          'hairline-strong':   '#34343a',
          'hairline-tertiary': '#3e3e44',
          accent:              '#5e6ad2',
          'accent-hover':      '#828fff',
          'accent-focus':      '#5e69d1',
          ink:                 '#f7f8f8',
          'ink-muted':         '#d0d6e0',
          'ink-subtle':        '#8a8f98',
          'ink-tertiary':      '#62666d',
          success:             '#27a644',
        },
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', '-apple-system', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SF Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        'linear-xs':   '4px',
        'linear-sm':   '6px',
        'linear-md':   '8px',
        'linear-lg':   '12px',
        'linear-xl':   '16px',
        'linear-pill': '9999px',
      },
    },
  },
  plugins: [],
}
