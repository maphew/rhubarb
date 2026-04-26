import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const baseSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  era: z.enum(["blogger", "drupal", "static"]).optional(),
  collection: z.string().optional(),
  sourceUrl: z.string().url().optional(),
  archivedAt: z.string().optional(),
  waybackTimestamp: z.string().optional(),
  published: z.union([z.string(), z.date()]).transform((v) =>
    typeof v === "string" ? v : v.toISOString().slice(0, 10)
  ).optional(),
  publishedRaw: z.string().optional(),
  heroImage: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

// Pull in extracted Markdown from /content at the repo root.
// The trailing slash + ../ navigates out of /src.
const recipes = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./content/recipes" }),
  schema: baseSchema,
});

const articles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./content/articles" }),
  schema: baseSchema,
});

const varieties = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./content/varieties" }),
  schema: baseSchema,
});

const pages = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./content/pages" }),
  schema: baseSchema,
});

const categories = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./content/categories" }),
  schema: baseSchema,
});

export const collections = { recipes, articles, varieties, pages, categories };
