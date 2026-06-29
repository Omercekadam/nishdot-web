/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./pages/**/*.html",
    "./users/**/*.html",
    "./events/**/*.html",
    "./jams/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          pink: "#EB596D",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
      },
      maxWidth: {
        container: "1440px",
      },
    },
  },
  plugins: [],
};
