/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./prerender.mjs"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#1A1E26", soft: "#454C59", faint: "#6B7280" },
        paper: { DEFAULT: "#FAFAF8", panel: "#F1F1EC", line: "#E2E2DA" },
        gx: { DEFAULT: "#C8102E", soft: "#FBEBEE" },
        kv: { DEFAULT: "#0E8A5F", soft: "#E9F6F0" },
        sy: { DEFAULT: "#005EB8", soft: "#E8F1FA" },
        common: { DEFAULT: "#6B5CA5", soft: "#F0EDF8" }
      },
      fontFamily: {
        sans: ["IBM Plex Sans JP", "Noto Sans JP", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"]
      }
    }
  },
  plugins: []
};
