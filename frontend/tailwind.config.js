// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'surface': '#0e0e10',
        'surface-container': '#19191c',
        'surface-container-low': '#131315',
        'surface-container-high': '#1f1f22',
        'surface-container-highest': '#262528',
        'surface-bright': '#2c2c2f',
        'surface-variant': '#262528',
        'on-surface': '#f6f3f5',
        'on-surface-variant': '#acaaad',
        'background': '#0e0e10',
        'on-background': '#f6f3f5',
        'primary': '#ba9eff',
        'primary-dim': '#8455ef',
        'primary-container': '#ae8dff',
        'on-primary': '#39008c',
        'secondary': '#34b5fa',
        'secondary-dim': '#17a8ec',
        'secondary-container': '#006591',
        'on-secondary': '#003047',
        'tertiary': '#9bffce',
        'tertiary-dim': '#58e7ab',
        'error': '#ff6e84',
        'outline': '#767577',
        'outline-variant': '#48474a',
      },
      fontFamily: {
        headline: ['Space Grotesk', 'sans-serif'],
        body: ['Manrope', 'sans-serif'],
        label: ['Manrope', 'sans-serif'],
      },
      animation: {
        'wave-float': 'wave-float 8s ease-in-out infinite',
        'led-pulse': 'led-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'wave-float': {
          '0%, 100%': { transform: 'translateY(0) scale(1)' },
          '50%': { transform: 'translateY(-10px) scale(1.05)' },
        },
        'led-pulse': {
          '0%, 100%': { opacity: '0.4', filter: 'blur(8px) brightness(0.8)' },
          '50%': { opacity: '1', filter: 'blur(12px) brightness(1.2)' },
        },
      },
    },
  },
  plugins: [],
}
