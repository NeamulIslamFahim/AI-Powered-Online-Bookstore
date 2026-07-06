/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        sand: "#f5efe4",
        bronze: "#9f5f2b",
        ember: "#6b2f16",
        mist: "#f9f7f1",
      },
      boxShadow: {
        card: "0 18px 60px rgba(23, 32, 51, 0.10)",
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "serif"],
        body: ["Manrope", "sans-serif"],
      },
    },
  },
  plugins: [],
};

