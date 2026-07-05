/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ocean: {
          navy: '#0a1628',
          teal: '#0d4f6b',
          coral: '#ff6b6b',
          seafoam: '#2dd4bf',
          gold: '#fbbf24',
          dark: '#050b14',
        }
      },
      animation: {
        'blob': 'blob 7s infinite',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        blob: {
          '0%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
          '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
          '100%': { transform: 'translate(0px, 0px) scale(1)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '1', filter: 'drop-shadow(0 0 10px rgba(45, 212, 191, 0.5))' },
          '50%': { opacity: '.7', filter: 'drop-shadow(0 0 20px rgba(45, 212, 191, 0.8))' },
        }
      }
    },
  },
  plugins: [],
}
