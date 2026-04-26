import { defineConfig } from "astro/config";
import { rewriteAssetUrls } from "./src/plugins/rewriteAssetUrls.mjs";

// Default to root-base so `npm run dev` / `npm run build` / `astro preview`
// just work locally. Override per-deploy:
//   GH Pages project site:  SITE=https://USER.github.io BASE=/rhubarb npm run build
//   Fly.io / custom domain: SITE=https://your.host BASE=/ npm run build
const site = process.env.SITE || "http://localhost:4321";
// Always trailing-slash; templates concatenate `${BASE}recipes/` etc.
const base = ((process.env.BASE || "/").replace(/\/+$/, "")) + "/";

export default defineConfig({
  site,
  base,
  trailingSlash: "ignore",
  build: {
    format: "directory",
  },
  markdown: {
    shikiConfig: { theme: "github-light" },
    remarkPlugins: [rewriteAssetUrls()],
  },
});
