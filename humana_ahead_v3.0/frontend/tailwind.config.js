/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#19281E',
        muted: '#657064',
        line: '#DDE4D7',
        panel: '#F7F8F4',
        brand: '#5C8727',
        'brand-dark': '#456B1D',
        'brand-soft': '#EDF3E4',
        forest: '#203126',
        gold: '#C89617',
      },
      boxShadow: {
        soft: '0 1px 3px rgba(25,40,30,.06), 0 1px 2px rgba(25,40,30,.04)',
      },
    },
  },
  plugins: [],
}
