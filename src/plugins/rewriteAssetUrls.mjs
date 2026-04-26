// Remark plugin: prepends Astro's `base` to site-absolute /_assets/ URLs in
// Markdown so images and links work whether the site is hosted at /rhubarb/
// (GH Pages project) or / (Fly.io / custom domain).
//
// Reads BASE from process.env at build time (the same env astro.config.mjs uses).

export function rewriteAssetUrls() {
  const raw = process.env.BASE ?? "/";
  const base = raw.endsWith("/") ? raw.slice(0, -1) : raw;
  if (base === "") return () => () => {};

  const walk = (node) => {
    if (!node || typeof node !== "object") return;
    if (
      (node.type === "image" || node.type === "link") &&
      typeof node.url === "string" &&
      node.url.startsWith("/_assets/")
    ) {
      node.url = base + node.url;
    }
    if (Array.isArray(node.children)) node.children.forEach(walk);
  };

  return () => walk;
}
