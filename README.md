# Industrial IDE Docs

A reference site that reorganizes the IDE manuals for Mitsubishi Electric **GX Works3**,
Keyence **KV STUDIO**, and Omron **Sysmac Studio** into a common 9-category structure
shared across all three vendors.
**Its primary purpose is discovery and reference by search engines and AI agents**
(ChatGPT/Claude, etc. via web search/browsing), so every page is pre-rendered as static
HTML. For human visitors, React (shadcn-style UI) hydrates on top to enable cross-page
search (⌘K) and a collapsible navigation.

## Mechanisms for AI/SEO

- **All 317 pages are rendered as static HTML at real URLs** — full text is readable even
  by crawlers that don't execute JS (search engines, AI `web_fetch`)
  - `/{vendor}/{slug}/`, e.g. `/gxworks3/06-01/`
- Per-page `<title>` / `<meta description>` / `canonical` / OGP / **JSON-LD (TechArticle + breadcrumbs)**
- `sitemap.xml` (all pages) / `robots.txt` (explicitly allows GPTBot, ClaudeBot, PerplexityBot, etc.)
- `llms.txt` — a full Markdown index for AI agents. Each section can be fetched directly at
  `content/{vendor}/{slug}.md`
- Every HTML page links to its Markdown source via `<link rel="alternate" type="text/markdown">`
- Prev/next section navigation plus full section links on category listing pages ensure
  crawlable paths

## Publishing steps (GitHub Pages)

1. Push the repository under the name `industrial-ide-docs`
   (to use a different name, just change `siteUrl` in `site.config.json` — the build is
   handled by CI)
2. Set Settings → Pages → Source to **GitHub Actions** (one-time setup)
3. From then on, every push to `main` triggers `.github/workflows/deploy.yml` to build and
   deploy automatically — both Markdown edits and UI changes go live within minutes of
   commit and push

After publishing, registering `sitemap.xml` with Google Search Console / Bing Webmaster
Tools will speed up indexing.

## Development

```bash
npm install
npm run dev      # dev server (SPA mode)
npm run build    # client + SSR build + pre-render 317 pages → dist/
```

## Regenerating content

The extraction pipeline from source PDFs is included under `tools/` (the source PDFs
themselves are not included).

```bash
pip install pymupdf
python tools/extract.py <gxworks3|kvstudio|sysmac>  # adjust SRC in the script for the PDF path
python tools/polish_content.py                       # repair PDF line wraps / labels / section overlap
python tools/audit_content.py                        # validate UTF-8, headings, tables and image links
python tools/build_index.py                          # regenerate nav / search / llms.txt
npm run build                                        # regenerate static HTML
```

## Sources and notes

- Each page's frontmatter / JSON-LD `isBasedOn` records the original manual name and page range
- About 2,700 figures/screenshots are cropped from the source PDFs and stored as WebP
  (`public/images/`, roughly 35MB total). Figures that failed detection are omitted
- Refer to each vendor's official manuals for accurate diagrams and the latest information
