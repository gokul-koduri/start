/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          primary: "#09090b",
          secondary: "#18181b",
          card: "#27272a",
          elevated: "#3f3f46",
        },
        accent: {
          blue: "#3b82f6",
          green: "#22c55e",
          red: "#ef4444",
          amber: "#f59e0b",
          purple: "#a855f7",
          cyan: "#06b6d4",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
