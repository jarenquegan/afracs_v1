/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        maroon: {
          darkest: '#350200',
          dark:    '#6C0200',
          DEFAULT: '#900500',
        },
        gold: {
          dark:    '#BD953E',
          DEFAULT: '#D4B356',
        },
      },
      fontFamily: {
        sans: ["'Helvetica Neue'", 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

