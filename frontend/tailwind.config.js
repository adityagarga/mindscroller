/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Brutalist all-caps stack — matches the workbench overlay.
        brutal: [
          '"Helvetica Neue"',
          '"Arial Black"',
          "Impact",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        ink: "#0a0a0b",
        panel: "#14141a",
        border: "#232328",
        muted: "#888888",
        accent: "#8b5cf6",
      },
    },
  },
  plugins: [],
};
