# -*- coding: utf-8 -*-
"""content/*.md を走査して nav.json / search-index.json / llms.txt を生成"""
import os, re, json, glob

ROOT = "/home/claude/work/site/public"
CONTENT = f"{ROOT}/content"

CATEGORIES = [
    ("setup",       "導入・画面・基本操作"),
    ("project",     "プロジェクト管理"),
    ("hardware",    "ハードウェア構成・パラメータ"),
    ("variables",   "変数・デバイス"),
    ("programming", "プログラミング"),
    ("transfer",    "接続・転送"),
    ("debug",       "モニタ・デバッグ・シミュレーション"),
    ("maintenance", "保守・セキュリティ・運用"),
    ("reference",   "リファレンス・付録"),
]
VENDORS = [
    ("gxworks3", "GX Works3", "三菱電機"),
    ("kvstudio", "KV STUDIO", "キーエンス"),
    ("sysmac",   "Sysmac Studio", "オムロン"),
]

def parse_fm(path):
    s = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    body = s[m.end():] if m else s
    heads = re.findall(r"^#{1,4}\s+(.+)$", body, re.M)
    return fm, heads, body

def sort_key(num):
    # "3.1" / "2-1" / "付2" / "A-3" / "9.0"
    m = re.match(r"^(?:付|A-?)(\d+)$", num)
    if m: return (99, int(m.group(1)), 0)
    parts = re.split(r"[.\-]", num)
    try: return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, 0)
    except ValueError: return (98, 0, 0)

nav = {"categories": [{"id": c, "label": l} for c, l in CATEGORIES],
       "vendors": [{"id": v, "label": l, "company": co} for v, l, co in VENDORS],
       "pages": []}
search = []

for vendor, vlabel, _ in VENDORS:
    for path in glob.glob(f"{CONTENT}/{vendor}/*.md"):
        fm, heads, body = parse_fm(path)
        slug = os.path.basename(path)[:-3]
        entry = dict(vendor=vendor, slug=slug, num=fm.get("num", ""),
                     title=fm.get("title", ""), cat=fm.get("category", "reference"))
        nav["pages"].append(entry)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
        text = re.sub(r"[|#*\-`>]", " ", text)
        text = re.sub(r"\s+", " ", text)
        search.append(dict(**entry, heads=heads[1:25],
                           excerpt=text[:180]))

# 共通ガイドは検索インデックスのみに追加(navには含めない)
for path in sorted(glob.glob(f"{CONTENT}/common/*.md")):
    slug = os.path.basename(path)[:-3]
    if slug == "index": continue
    fm, heads, body = parse_fm(path)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    text = re.sub(r"[|#*\-`>]", " ", text)
    text = re.sub(r"\s+", " ", text)
    search.append(dict(vendor="common", slug=slug, num="",
                       title=fm.get("title", slug) + "(3社対応表)",
                       cat=slug, heads=heads[1:25], excerpt=text[:180]))

nav["pages"].sort(key=lambda p: (p["vendor"], sort_key(p["num"])))

with open(f"{ROOT}/nav.json", "w", encoding="utf-8") as f:
    json.dump(nav, f, ensure_ascii=False)
with open(f"{ROOT}/search-index.json", "w", encoding="utf-8") as f:
    json.dump(search, f, ensure_ascii=False)

# llms.txt
lines = ["# Industrial IDE Docs — GX Works3 / KV STUDIO / Sysmac Studio 共通構造リファレンス", "",
         "> 三菱電機 GX Works3・キーエンス KV STUDIO・オムロン Sysmac Studio のマニュアルを、",
         "> 3社共通の9カテゴリ構造で再編したAI探索向けドキュメント。各ページはMarkdownで直接取得可能。",
         "> 図・スクリーンショットは images/ 配下のWebPとして収録(Markdown内の相対パスはサイトルート基準)。", ""]
lines += ["## 共通ガイド(3社対応表)", ""]
lines.append("- [全体ガイド・概念対応表](content/common/index.md)")
for c, l in CATEGORIES:
    lines.append(f"- [{l}](content/common/{c}.md)")
lines.append("")
for vendor, vlabel, co in VENDORS:
    lines += [f"## {vlabel} ({co})", ""]
    pages = [p for p in nav["pages"] if p["vendor"] == vendor]
    for c, cl in CATEGORIES:
        cat_pages = [p for p in pages if p["cat"] == c]
        if not cat_pages: continue
        lines.append(f"### {cl}")
        for p in cat_pages:
            lines.append(f"- [{p['num']} {p['title']}](content/{vendor}/{p['slug']}.md)")
        lines.append("")
with open(f"{ROOT}/llms.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("pages:", len(nav["pages"]),
      "| search:", len(search),
      "| llms.txt:", os.path.getsize(f"{ROOT}/llms.txt"), "bytes",
      "| search-index:", os.path.getsize(f"{ROOT}/search-index.json"), "bytes")
from collections import Counter
print(Counter((p["vendor"], p["cat"]) for p in nav["pages"]))
