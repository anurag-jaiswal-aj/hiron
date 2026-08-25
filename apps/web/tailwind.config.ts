import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      keyframes: {
        scan: {
          "0%, 100%": { top: "10%" },
          "50%": { top: "90%" },
        },
        extract: {
          "0%": { left: "0%", opacity: "0" },
          "20%": { opacity: "1" },
          "80%": { opacity: "1" },
          "100%": { left: "100%", opacity: "0" },
        },
        "extract-vertical": {
          "0%": { top: "-30%", opacity: "0" },
          "20%": { opacity: "1" },
          "80%": { opacity: "1" },
          "100%": { top: "100%", opacity: "0" },
        },
      },
      animation: {
        scan: "scan 3s ease-in-out infinite",
        extract: "extract 2s linear infinite",
        "extract-vertical": "extract-vertical 2s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
