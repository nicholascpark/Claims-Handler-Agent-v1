/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        'intact-red': '#E31937',
        'intact-dark-red': '#B01429',
      },
    },
  },
  plugins: [],
}
