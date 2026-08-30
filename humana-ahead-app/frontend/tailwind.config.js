/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0f172a',
        muted: '#64748b',
        line: '#e2e8f0',
        panel: '#f8fafc',
        brand: '#0f6c78',
        'brand-soft': '#e8f4f5',
      },
      boxShadow: { soft: '0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04)' },
    },
  },
  plugins: [],
}
