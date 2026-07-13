export type Vendor = "gxworks3" | "kvstudio" | "sysmac" | "common";

export interface PageMeta { vendor: string; slug: string; num: string; title: string; cat: string; }
export interface Nav {
  categories: { id: string; label: string }[];
  vendors: { id: string; label: string; company: string }[];
  pages: PageMeta[];
}
export interface SearchDoc extends PageMeta { heads: string[]; excerpt: string; }

export const VENDOR_META: Record<string, { label: string; company: string; accent: string; soft: string; border: string }> = {
  gxworks3: { label: "GX Works3", company: "三菱電機", accent: "text-gx", soft: "bg-gx-soft", border: "border-gx" },
  kvstudio: { label: "KV STUDIO", company: "キーエンス", accent: "text-kv", soft: "bg-kv-soft", border: "border-kv" },
  sysmac:   { label: "Sysmac Studio", company: "オムロン", accent: "text-sy", soft: "bg-sy-soft", border: "border-sy" },
  common:   { label: "共通ガイド", company: "3社対応表", accent: "text-common", soft: "bg-common-soft", border: "border-common" },
};

const base = import.meta.env.BASE_URL;

let navCache: Nav | null = null;
export async function loadNav(): Promise<Nav> {
  if (navCache) return navCache;
  const res = await fetch(`${base}nav.json`);
  navCache = await res.json();
  return navCache!;
}

let searchCache: SearchDoc[] | null = null;
export async function loadSearch(): Promise<SearchDoc[]> {
  if (searchCache) return searchCache;
  const res = await fetch(`${base}search-index.json`);
  searchCache = await res.json();
  return searchCache!;
}

const mdCache = new Map<string, string>();
export async function loadMarkdown(vendor: string, slug: string): Promise<string> {
  const key = `${vendor}/${slug}`;
  if (mdCache.has(key)) return mdCache.get(key)!;
  const res = await fetch(`${base}content/${vendor}/${slug}.md`);
  if (!res.ok) throw new Error(`not found: ${key}`);
  const raw = await res.text();
  const body = raw.replace(/^---[\s\S]*?---\n/, "");
  mdCache.set(key, body);
  return body;
}

export function frontmatterOf(raw: string): Record<string, string> {
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  const fm: Record<string, string> = {};
  if (m) for (const line of m[1].split("\n")) {
    const i = line.indexOf(":");
    if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^"|"$/g, "");
  }
  return fm;
}
