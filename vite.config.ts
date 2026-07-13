import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import config from "./site.config.json";

// base は site.config.json の siteUrl から導出(リポジトリ名変更時はそちらを編集)
const base = new URL(config.siteUrl).pathname;

export default defineConfig({
  base,
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
