// dist/ の SPA シェルをもとに、全ルートを静的HTML化して SEO/AI クローラから読めるようにする
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { render } from "./dist-ssr/entry-server.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(fs.readFileSync(path.join(__dirname, "site.config.json"), "utf-8"));
const SITE = config.siteUrl.replace(/\/$/, "/"); // 末尾スラッシュ保証
const BASE = new URL(SITE).pathname;             // 例: /industrial-ide-docs/
const DIST = path.join(__dirname, "dist");

const nav = JSON.parse(fs.readFileSync(path.join(DIST, "nav.json"), "utf-8"));
const searchIndex = JSON.parse(fs.readFileSync(path.join(DIST, "search-index.json"), "utf-8"));
const shell = fs.readFileSync(path.join(DIST, "index.html"), "utf-8");

const CAT_LABELS = {
  setup: "導入・画面・基本操作", project: "プロジェクト管理", hardware: "ハードウェア構成・パラメータ",
  variables: "変数・デバイス", programming: "プログラミング", transfer: "接続・転送",
  debug: "モニタ・デバッグ・シミュレーション", maintenance: "保守・セキュリティ・運用", reference: "リファレンス・付録",
};
const VENDOR_LABELS = { gxworks3: "GX Works3(三菱電機)", kvstudio: "KV STUDIO(キーエンス)", sysmac: "Sysmac Studio(オムロン)", common: "共通ガイド" };

function readMd(vendor, slug) {
  const raw = fs.readFileSync(path.join(DIST, "content", vendor, `${slug}.md`), "utf-8");
  const m = raw.match(/^---\n([\s\S]*?)\n---\n/);
  const fm = {};
  if (m) for (const line of m[1].split("\n")) {
    const i = line.indexOf(":");
    if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^"|"$/g, "");
  }
  return { fm, body: m ? raw.slice(m[0].length) : raw };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
const safeJson = (o) => JSON.stringify(o).replace(/</g, "\\u003c");

function head({ title, description, urlPath, mdPath, jsonld }) {
  const url = new URL(urlPath.replace(/^\//, ""), SITE).href;
  let h = `<title>${esc(title)}</title>\n`;
  h += `<meta name="description" content="${esc(description)}" />\n`;
  h += `<link rel="canonical" href="${url}" />\n`;
  h += `<meta property="og:title" content="${esc(title)}" />\n`;
  h += `<meta property="og:description" content="${esc(description)}" />\n`;
  h += `<meta property="og:type" content="article" />\n`;
  h += `<meta property="og:url" content="${url}" />\n`;
  h += `<meta property="og:site_name" content="${esc(config.siteName)}" />\n`;
  if (mdPath) h += `<link rel="alternate" type="text/markdown" href="${new URL(mdPath, SITE).href}" title="Markdown原文" />\n`;
  if (jsonld) h += `<script type="application/ld+json">${safeJson(jsonld)}</script>\n`;
  return h;
}

function writePage(routePath, htmlBody, headHtml, preload) {
  let out = shell
    .replace(/<title>[\s\S]*?<\/title>\n?/, "")
    .replace(/<meta name="description"[^>]*\/>\n?/, "")
    .replace("</head>", headHtml + "</head>")
    .replace('<div id="root"></div>', `<div id="root">${htmlBody}</div>\n<script>window.__PRELOAD__=${safeJson(preload)}</script>`);
  const dir = routePath === "/" ? DIST : path.join(DIST, routePath.replace(/^\//, ""));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "index.html"), out);
}

const routes = [];

// トップページ
{
  const { body } = readMd("common", "index");
  const preload = { route: "/", page: { vendor: "common", slug: "index", md: body, title: "Industrial IDE Docs", num: "", cat: "index" } };
  const html = render(BASE, preload, BASE);
  const jsonld = {
    "@context": "https://schema.org", "@type": "WebSite",
    name: config.siteName, url: SITE, description: config.description, inLanguage: "ja",
  };
  writePage("/", html, head({
    title: "Industrial IDE Docs — GX Works3 / KV STUDIO / Sysmac Studio 共通構造リファレンス",
    description: config.description, urlPath: "/", mdPath: "content/common/index.md", jsonld,
  }), preload);
  routes.push("/");
}

// 共通カテゴリページ
for (const c of nav.categories) {
  const { body } = readMd("common", c.id);
  const catPages = nav.pages.filter((p) => p.cat === c.id);
  const preload = { route: `/common/${c.id}`, page: { vendor: "common", slug: c.id, md: body, title: c.label, num: "", cat: c.id }, catPages };
  const html = render(`${BASE}common/${c.id}`, preload, BASE);
  const desc = `${c.label}に関するGX Works3・KV STUDIO・Sysmac Studioの用語対応表と、3社マニュアルの該当節一覧。`;
  const jsonld = {
    "@context": "https://schema.org", "@type": "TechArticle",
    headline: `${c.label} — 3社対応表`, inLanguage: "ja",
    isPartOf: { "@type": "WebSite", name: config.siteName, url: SITE },
  };
  writePage(`/common/${c.id}`, html, head({
    title: `${c.label} — 3社対応表 | Industrial IDE Docs`,
    description: desc, urlPath: `common/${c.id}/`, mdPath: `content/common/${c.id}.md`, jsonld,
  }), preload);
  routes.push(`/common/${c.id}`);
}

// ベンダー各節
for (const vendor of ["gxworks3", "kvstudio", "sysmac"]) {
  const list = nav.pages.filter((p) => p.vendor === vendor);
  list.forEach((p, i) => {
    const { fm, body } = readMd(vendor, p.slug);
    const sd = searchIndex.find((d) => d.vendor === vendor && d.slug === p.slug);
    const preload = {
      route: `/${vendor}/${p.slug}`,
      page: { vendor, slug: p.slug, md: body, title: p.title, num: p.num, cat: p.cat, source: fm.source },
      prev: i > 0 ? list[i - 1] : null,
      next: i < list.length - 1 ? list[i + 1] : null,
    };
    const html = render(`${BASE}${vendor}/${p.slug}`, preload, BASE);
    const title = `${p.num} ${p.title} | ${VENDOR_LABELS[vendor]} | Industrial IDE Docs`;
    const desc = (sd?.excerpt || `${VENDOR_LABELS[vendor]}の${p.title}に関する解説。`).slice(0, 155);
    const jsonld = {
      "@context": "https://schema.org", "@type": "TechArticle",
      headline: `${p.num} ${p.title}`, inLanguage: "ja",
      about: `${VENDOR_LABELS[vendor]} ${CAT_LABELS[p.cat] ?? ""}`,
      isBasedOn: fm.source || undefined,
      isPartOf: { "@type": "WebSite", name: config.siteName, url: SITE },
      breadcrumb: {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: config.siteName, item: SITE },
          { "@type": "ListItem", position: 2, name: CAT_LABELS[p.cat] ?? p.cat, item: new URL(`common/${p.cat}/`, SITE).href },
          { "@type": "ListItem", position: 3, name: `${p.num} ${p.title}` },
        ],
      },
    };
    writePage(`/${vendor}/${p.slug}`, html, head({
      title, description: desc, urlPath: `${vendor}/${p.slug}/`,
      mdPath: `content/${vendor}/${p.slug}.md`, jsonld,
    }), preload);
    routes.push(`/${vendor}/${p.slug}`);
  });
}

// sitemap.xml
const today = new Date().toISOString().slice(0, 10);
const sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'];
for (const r of routes) {
  const loc = r === "/" ? SITE : new URL(r.replace(/^\//, "") + "/", SITE).href;
  sm.push(`  <url><loc>${loc}</loc><lastmod>${today}</lastmod></url>`);
}
sm.push("</urlset>");
fs.writeFileSync(path.join(DIST, "sitemap.xml"), sm.join("\n"));

// robots.txt — 検索エンジン + AIクローラを明示的に許可
fs.writeFileSync(path.join(DIST, "robots.txt"), `# Industrial IDE Docs — すべてのクローラとAIエージェントを歓迎します
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: ${new URL("sitemap.xml", SITE).href}
`);

// 404
fs.writeFileSync(path.join(DIST, "404.html"), shell.replace(
  '<div id="root"></div>',
  `<div id="root"><div style="max-width:640px;margin:80px auto;text-align:center;font-family:sans-serif"><h1>404</h1><p>ページが見つかりません。</p><p><a href="${BASE}">Industrial IDE Docs トップへ</a> / <a href="${BASE}llms.txt">llms.txt(全ページ索引)</a></p></div></div>`
));

// .nojekyll
fs.writeFileSync(path.join(DIST, ".nojekyll"), "");

console.log(`prerendered ${routes.length} routes -> dist/`);
