import type { Config } from "tailwindcss";

// One aesthetic: off-white paper, ink, one red-orange accent. Colours are named by role so
// a palette change is one edit.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f4f1ea",
        ink: "#16130f",
        muted: "#6b645a",
        rule: "#16130f",
        hair: "#d9d3c7",
        accent: "#e2401c",
        accentsoft: "#fbd9cc",
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        serif: ["Newsreader", "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
