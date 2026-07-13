# -*- coding: utf-8 -*-
"""
GX Works3 / KV STUDIO / Sysmac Studio マニュアル → AI探索向けMarkdown抽出パイプライン
- しおり(TOC)から節単位でページ範囲を切り出し
- ヘッダ/フッタ/サイドタブを座標+正規表現で除去
- フォントサイズで見出し階層を復元、表はfind_tablesでMarkdownテーブル化
- ベンダ固有の参照表記・記号を正規化し、3社共通のカテゴリ構造へマッピング
"""
import fitz, re, os, io, json, unicodedata
from collections import defaultdict
from PIL import Image

IMG_OUT = "/home/claude/work2/user-site/public/images"
IMG_ZOOM = 2.0
IMG_MAX_W = 1600
IMG_QUALITY = 76

SRC = "/home/claude/work/pdfs"
OUT = "/home/claude/work2/user-site/public/content"

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
CAT_IDS = [c[0] for c in CATEGORIES]

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)

# ---------------------------------------------------------------- vendor configs
VENDORS = {
    "gxworks3": dict(
        file=f"{SRC}/GXWorks3オペレーティングマニュアル.pdf",
        label="GX Works3", company="三菱電機",
        manual="GX Works3 オペレーティングマニュアル (SH-081214)",
        body_box=(35, 42, 545, 782),      # x0,y0,x1,y1 本文領域
        drop_res=[r"^\d+\s*$", r"^MEMO$"],
        title_size=15.0,                   # 節タイトル(ユニット境界)サイズ下限
        h_tiers=[(12.6, 2), (11.6, 3), (10.5, 4)],  # (size下限, 見出しレベル)
        bullet_map={"■": "**", "●": "- ", "・": "  - "},
    ),
    "kvstudio": dict(
        file=f"{SRC}/AS_151666_KV-8000_KV-5000_3000_KV-7000_UM_084917_KJ_JP_2045_1 (1).pdf",
        label="KV STUDIO", company="キーエンス",
        manual="KV STUDIO Ver.12 ユーザーズマニュアル (AS_151666)",
        body_box=(30, 50, 480, 700),
        drop_res=[r"^\d+-\d+\s*$", r"^－\s*KV STUDIO", r"^\d+\s*$", r"^MEMO$"],
        title_size=16.0, autostart=True,
        h_tiers=[(11.5, 2), (10.4, 3)],
        bullet_map={"■": "**", "●": "- ", "・": "  - "},
    ),
    "sysmac": dict(
        file=f"{SRC}/sbca-470am_sysmac-se2___.pdf",
        label="Sysmac Studio", company="オムロン",
        manual="Sysmac Studio Version 1 オペレーションマニュアル (SBCA-470)",
        body_box=(40, 55, 500, 788),
        drop_res=[r"^Sysmac Studio Version 1", r"^\d+-\d+\s*$", r"^\d+\s*$",
                  r"^付\s*-\s*\d+$", r"^A-\d+\s*$", r"^MEMO$"],
        title_size=17.0,
        h_tiers=[(13.2, 2), (11.5, 3)],
        bullet_map={"l": "- ", "●": "- ", "・": "  - "},
    ),
}

# ---------------------------------------------------------------- unit builders
def slug_num(num):
    """'3.1'/'2-1'/'4-1' -> '03-01', '付2'/'A-3' -> 'ap-02'/'ap-03'"""
    m = re.match(r"^(?:付|A-?)(\d+)$", num)
    if m: return f"ap-{int(m.group(1)):02d}"
    parts = re.split(r"[.\-]", num)
    return "-".join(f"{int(p):02d}" for p in parts if p.isdigit())

def build_units_gxw3(toc):
    """レベル3(X.Y節)をユニット化。付録はレベル2(付N)単位。付1(改版履歴)等は除外。"""
    units, cur_chap = [], None
    cat_by_chap = {1:"setup",2:"setup",3:"project",4:"hardware",5:"variables",
                   6:"programming",7:"variables",8:"variables",9:"programming",
                   10:"programming",11:"debug",12:"transfer",13:"transfer",
                   14:"debug",15:"maintenance",16:"maintenance",17:"debug",18:"maintenance"}
    skip_ap = {"付1"}  # バージョン別変更履歴112pは除外
    for i,(lv,title,page) in enumerate(toc):
        m = re.match(r"^(\d+)\s+(.+)$", title)
        if lv==2 and m: cur_chap = int(m.group(1))
        m3 = re.match(r"^(\d+\.\d+)\s+(.+)$", title)
        ma = re.match(r"^(付\d+)\s+(.+)$", title)
        if lv==3 and m3 and cur_chap:
            units.append(dict(num=m3.group(1), title=m3.group(2), page=page,
                              cat=cat_by_chap.get(cur_chap,"reference"), toc_i=i, sub_lv=4))
        elif lv==2 and ma and ma.group(1) not in skip_ap:
            units.append(dict(num=ma.group(1), title=ma.group(2), page=page,
                              cat="reference", toc_i=i, sub_lv=3))
    breaks = sorted({p for lv,t,p in toc if lv==1} |
                    {p for lv,t,p in toc if lv==2 and re.match(r"^(付1|\d+)\s", t)})
    # 章冒頭の概要ページ(章開始<最初の節開始)を「X.0 機能概要」ユニット化
    chap_pages = {}
    for lv,t,p in toc:
        m = re.match(r"^(\d+)\s+(.+)$", t)
        if lv==2 and m: chap_pages[int(m.group(1))] = (p, m.group(2))
    extra = []
    for chap,(cp,ct) in chap_pages.items():
        firsts = [u for u in units if u["num"].startswith(f"{chap}.")]
        if firsts and firsts[0]["page"] > cp:
            extra.append(dict(num=f"{chap}.0", title=f"{ct}(機能概要)", page=cp,
                              cat=cat_by_chap.get(chap,"reference"), toc_i=0,
                              sub_lv=4, autostart=True))
    units = sorted(units + extra, key=lambda u: (u["page"], u["num"]))
    return units, breaks

def build_units_kvs(toc):
    cat_by_chap = {1:"setup",2:"project",3:"hardware",4:"project",5:"programming",
                   6:"setup",7:"programming",8:"programming",9:"debug",10:"debug",
                   11:"debug",12:"maintenance",13:"programming"}
    overrides = {"6-2":"hardware","9-1":"transfer"}
    units, in_ap = [], False
    for i,(lv,title,page) in enumerate(toc):
        if lv==1 and title.startswith("付"): in_ap = True
        m = re.match(r"^(\d+-\d+)\s+(.+)$", title)
        if lv==2 and m and not in_ap:
            num = m.group(1); chap = int(num.split("-")[0])
            units.append(dict(num=num, title=m.group(2), page=page,
                              cat=overrides.get(num, cat_by_chap.get(chap,"reference")),
                              toc_i=i, sub_lv=3))
        elif lv==2 and in_ap:
            ma = re.match(r"^(\d+)\s+(.+)$", title)
            if ma and "改訂履歴" not in title:
                units.append(dict(num=f"付{ma.group(1)}", title=ma.group(2), page=page,
                                  cat="reference", toc_i=i, sub_lv=3))
    breaks = sorted({p for lv,t,p in toc if lv==1} |
                    {p for lv,t,p in toc if lv==2 and "改訂履歴" in t})
    return units, breaks

def build_units_sys(toc):
    cat_by_chap = {1:"setup",2:"setup",3:"setup",4:"programming",5:"hardware",
                   6:"transfer",7:"debug",8:"maintenance",9:"programming",
                   10:"reference",11:"reference"}
    overrides = {"3-3":"project","4-1":"variables","4-3":"variables","4-4":"variables"}
    units = []
    skip = {"A-13","A-14"}
    for i,(lv,title,page) in enumerate(toc):
        m = re.match(r"^(\d+-\d+)\s+(.+)$", title)
        ma = re.match(r"^(A-\d+)\s+(.+)$", title)
        if lv==2 and m:
            num = m.group(1); chap = int(num.split("-")[0])
            if chap<=11:
                units.append(dict(num=num, title=m.group(2), page=page,
                                  cat=overrides.get(num, cat_by_chap.get(chap,"reference")),
                                  toc_i=i, sub_lv=3))
        elif lv==2 and ma and ma.group(1) not in skip:
            units.append(dict(num=ma.group(1), title=ma.group(2), page=page,
                              cat="reference", toc_i=i, sub_lv=3))
    breaks = sorted({p for lv,t,p in toc if lv==1} |
                    {p for lv,t,p in toc if lv==2 and re.match(r"^A-1[34]\s", t)})
    return units, breaks

BUILDERS = {"gxworks3": build_units_gxw3, "kvstudio": build_units_kvs, "sysmac": build_units_sys}

# ---------------------------------------------------------------- figure detection
def _overlap(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy

def _area(r): return max(0, r[2]-r[0]) * max(0, r[3]-r[1])

def detect_figures(page, cfg, table_bboxes):
    """スクリーンショット(ラスタ)+ベクタ作図の領域を検出して矩形リストを返す"""
    x0, y0, x1, y1 = cfg["body_box"]
    cands = []
    # ラスタ画像
    for info in page.get_image_info():
        r = list(info["bbox"])
        if r[2]-r[0] < 100 or r[3]-r[1] < 40: continue          # インラインアイコン除外
        if any(_overlap(r, tb) > 0.6*_area(r) for tb in table_bboxes): continue  # 表内画像除外
        cands.append((r, True))
    # ベクタ作図クラスタ
    try:
        drawings = page.get_drawings()
        clusters = page.cluster_drawings(drawings=drawings)
    except Exception:
        drawings, clusters = [], []
    for c in clusters:
        r = [c.x0, c.y0, c.x1, c.y1]
        if r[2]-r[0] < 150 or r[3]-r[1] < 60: continue
        if any(_overlap(r, tb) > 0.4*_area(r) for tb in table_bboxes): continue  # 表と重複
        has_raster = any(_overlap(r, cr) > 0 for cr, is_r in cands if is_r)
        n_items = sum(1 for d in drawings
                      if _overlap(r, [d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1]) > 0)
        if not has_raster and n_items < 6: continue              # 枠だけの注記ボックス等は除外
        cands.append((r, False))
    # 本文領域外・ページ全面は除外
    page_area = _area([page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1])
    cands = [(r, ir) for r, ir in cands
             if _overlap(r, [x0, y0, x1, y1]) > 0.5*_area(r) and _area(r) < 0.92*page_area]
    # 重複矩形をマージ
    rects = [r for r, _ in cands]
    merged = []
    for r in sorted(rects, key=lambda r: (r[1], r[0])):
        for m in merged:
            if _overlap(r, m) > 0.25 * min(_area(r), _area(m)):
                m[0] = min(m[0], r[0]); m[1] = min(m[1], r[1])
                m[2] = max(m[2], r[2]); m[3] = max(m[3], r[3])
                break
        else:
            merged.append(list(r))
    return merged

def render_figure(page, rect, vendor, slug, seq, page_no):
    os.makedirs(f"{IMG_OUT}/{vendor}", exist_ok=True)
    clip = fitz.Rect(rect) & page.rect
    if clip.is_empty: return None
    pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(IMG_ZOOM, IMG_ZOOM))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    if img.width > IMG_MAX_W:
        img = img.resize((IMG_MAX_W, int(img.height * IMG_MAX_W / img.width)), Image.LANCZOS)
    fname = f"{slug}-{seq:02d}.webp"
    img.save(f"{IMG_OUT}/{vendor}/{fname}", "WEBP", quality=IMG_QUALITY)
    return f"![図(元マニュアル p.{page_no})](images/{vendor}/{fname})"

# ---------------------------------------------------------------- block extraction
def page_items(page, cfg, table_bboxes, fig_bboxes=()):
    """本文領域内のテキストブロックを (y, x, kind, text, size, bold) で返す"""
    x0,y0,x1,y1 = cfg["body_box"]
    items = []
    d = page.get_text("dict")
    for b in d["blocks"]:
        if b["type"] != 0: continue
        lines, maxsz, bold = [], 0.0, False
        by0 = bx0 = None
        for l in b["lines"]:
            if abs(l["dir"][0]) < 0.5: continue  # 縦書き(サイドタブ)除去
            lx0,ly0,lx1,ly1 = l["bbox"]
            cx, cy = (lx0+lx1)/2, (ly0+ly1)/2
            if not (x0 <= cx <= x1 and y0 <= cy <= y1): continue  # 行単位で余白除去
            if any(tb[0]-2<=cx<=tb[2]+2 and tb[1]-2<=cy<=tb[3]+2 for tb in table_bboxes):
                continue  # 表領域内の行は除外(表として別途出力)
            if any(fb[0]-1<=cx<=fb[2]+1 and fb[1]-1<=cy<=fb[3]+1 for fb in fig_bboxes):
                continue  # 図領域内のテキストは図として出力するため除外
            t = "".join(s["text"] for s in l["spans"])
            if not t.strip(): continue
            lines.append(t)
            if by0 is None: by0, bx0 = ly0, lx0
            for s in l["spans"]:
                if s["text"].strip():
                    maxsz = max(maxsz, s["size"])
                    if s["flags"] & 16: bold = True
        if not lines: continue
        text = join_lines(lines)
        if not text.strip(): continue
        if any(re.match(rx, text.strip()) for rx in cfg["drop_res"]): continue
        items.append([by0, bx0, "text", text, maxsz, bold])
    return items

def join_lines(lines):
    """日本語連結: 行末尾がCJKなら空白なし、ASCII同士は空白で連結"""
    out = ""
    for ln in lines:
        ln = ln.rstrip()
        if not out: out = ln; continue
        a, b = out[-1], ln[:1]
        if re.match(r"[0-9A-Za-z)\]%.,:;]", a) and re.match(r"[0-9A-Za-z(\[]", b):
            out += " " + ln
        else:
            out += ln
    return out

def _table_rows(tbl, vendor):
    rows = tbl.extract()
    rows = [[map_pua(vendor, re.sub(r"\s*\n\s*", " ", (c or ""))).strip() for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    return rows

def _rows_to_md(rows):
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # 全行で空の列を削除
    keep = [ci for ci in range(ncol) if any(r[ci] for r in rows)]
    if len(keep) < 2: return None
    rows = [[r[ci] for ci in keep] for r in rows]
    ncol = len(keep)
    filled = sum(1 for r in rows for c in r if c)
    fill = filled / (len(rows) * ncol)
    # 誤検出とみられる小規模・低充足の表はテキストに降格
    if len(rows) <= 3 and fill < 0.40:
        return "\n\n".join(" ".join(c for c in r if c) for r in rows if any(r))
    if len(rows) < 2 or fill < 0.2: return None
    def esc(c): return c.replace("|", "\\|")
    md = "| " + " | ".join(esc(c) for c in rows[0]) + " |\n"
    md += "|" + "---|" * ncol + "\n"
    for r in rows[1:]:
        md += "| " + " | ".join(esc(c) for c in r) + " |\n"
    return md

def page_tables(page, vendor):
    """表の検出→分割ヘッダの結合→Markdown化。[(bbox, md_or_text, is_table)]を返す"""
    try:
        tf = page.find_tables()
    except Exception:
        return []
    raw = []
    for t in tf.tables:
        rows = _table_rows(t, vendor)
        if not rows: continue
        raw.append([list(t.bbox), rows])
    raw.sort(key=lambda x: x[0][1])
    # 縦に隣接し列数が同じ表を結合(ヘッダ分割対策)
    merged = []
    for bb, rows in raw:
        if merged:
            pbb, prows = merged[-1]
            same_cols = max(len(r) for r in rows) == max(len(r) for r in prows)
            if (same_cols and 0 <= bb[1] - pbb[3] < 10
                    and abs(bb[0] - pbb[0]) < 20 and abs(bb[2] - pbb[2]) < 20):
                prows.extend(rows)
                pbb[2] = max(pbb[2], bb[2]); pbb[3] = bb[3]
                continue
        merged.append([bb, rows])
    out = []
    for bb, rows in merged:
        md = _rows_to_md(rows)
        if md is None: continue
        out.append((bb, md, md.lstrip().startswith("|")))
    return out

# ---------------------------------------------------------------- unit rendering
def render_unit(doc, cfg, unit, next_unit, subheads):
    p_start = unit["page"]-1
    p_end = min(unit["page_end"], doc.page_count) - 1
    if next_unit and next_unit["page"] > unit["page_end"]:
        next_unit = None  # クランプ済なら次節境界チェック不要
    parts, started = [], bool(cfg.get("autostart")) or bool(unit.get("autostart"))
    title_n = norm(unit["num"] + unit["title"])
    next_n = norm(next_unit["num"] + next_unit["title"]) if next_unit else None
    sub_by_norm = {norm(t): lv for (lv, t, pg) in subheads}

    key = norm(unit["num"]) + norm(unit["title"])[:10]
    for pn in range(p_start, p_end+1):
        page = doc[pn]
        tables = page_tables(page, unit["_vendor"])
        figs = detect_figures(page, cfg, [bb for bb, _, _ in tables])
        items = page_items(page, cfg, [bb for bb, _, _ in tables], figs)
        for bb, md, is_tab in tables:
            items.append([bb[1], bb[0], "table" if is_tab else "p", md, 0, False])
        for fb in figs:
            md_img = render_figure(page, fb, unit["_vendor"], unit["slug"], unit["_figseq"], pn+1)
            if md_img:
                items.append([fb[1], fb[0], "img", md_img, 0, False])
                unit["_figseq"] += 1
        items.sort(key=lambda it: (round(it[0],1), it[1]))

        for it in items:
            y, x, kind, text, sz, bold = it
            tn = norm(text)
            if pn > p_start and not started:
                started = True
            if pn == p_start and not started:
                if key in tn or tn == title_n:
                    started = True
                    continue  # ユニットタイトル自体は出力しない(H1はfrontmatter側)
                else:
                    continue
            if not started and sz >= cfg["title_size"]:
                started = True
                continue
            if not started:
                continue
            if sz >= cfg["title_size"] and (title_n in tn or key in tn):
                continue  # タイトル再掲は捨てる
            if pn == p_end and next_n and (sz >= cfg["title_size"] or tn == next_n):
                return parts, started
            if kind == "table":
                parts.append(("table", text)); continue
            if kind == "img":
                parts.append(("img", text)); continue
            # 見出し判定: TOC一致を優先、次にサイズ
            matched = None
            for k, lv in sub_by_norm.items():
                if tn == k or (len(k) > 6 and tn.startswith(k)):
                    matched = lv; break
            if matched:
                ht = re.sub(r"^((?:\d+|付\d*|A)(?:[.\-]\d+)*)(?=[^\d\s.\-])", r"\1 ", text.strip())
                parts.append(("h", "#"*min(matched,5) + " " + ht))
                continue
            # 操作手順の番号(大フォント)を段落化
            ms = re.match(r"^([1-9]\d?)(\D.{10,})", text)
            if ms and sz >= 11 and (len(text) >= 26 or
                    text.rstrip().endswith(("。", "ます", "さい", "す)", "す）"))):
                parts.append(("p", f"{ms.group(1)}. {ms.group(2).strip()}")); continue
            if sz >= cfg["title_size"]:  # 境界検出漏れ対策
                parts.append(("h", "## " + text.strip())); continue
            hlv = None
            for smin, lv in cfg["h_tiers"]:
                if (sz >= smin and bold and len(text) < 70 and not text.endswith("。")
                        and not re.match(r"^[1-9]\d?[^\d.\-]", text)):
                    hlv = lv; break
            if hlv:
                parts.append(("h", "#"*hlv + " " + text.strip()))
            else:
                parts.append(("p", text))
    return parts, started

# ---------------------------------------------------------------- post-processing
# PUAグリフ → 出力文字列(凡例文+ピクセル形状解析で確定、キー記号はCodex裏取り待ち)
PUA_MAP_COMMON = {
    "\uf0ae": "→",    # Symbol 0xAE 右矢印
    "\uf0d7": "・",   # Symbol 0xD7 箇条書き点
}
PUA_MAP = {
    "gxworks3": {
        **PUA_MAP_COMMON,
        "\uf0c6": "○", "\uf0c7": "△", "\uf0c8": "×", "\uf0c9": "―",
        "\uf06f": "□",              # Wingdings 'o' プレースホルダ
        "\uf0f0": " ⇒ ",            # Wingdings メニュー経路矢印
        "\uf0c0": "→ ",             # マニュアル参照アイコン
        "\uf0c1": "→ ",             # ページ参照アイコン
        "\uf0fb": "・",             # 機能項目アイコン
        "\uf083": "[Ctrl]", "\uf084": "[Shift]", "\uf08f": "[Enter]",
        "\uf081": "[Tab]", "\uf082": "[Alt]", "\uf085": "[Esc]", "\uf08c": "[Space]",
        "\uf0bc": "[↑]", "\uf0bd": "[↓]", "\uf0be": "[←]", "\uf0bf": "[→]",
    },
    "kvstudio": {
        **PUA_MAP_COMMON,
        "\uf06c": "●", "\uf06e": "■",   # Wingdings l/n
        "\uf075": "►", "\uf067": "→",   # Wingdings3(Codex裏取り済)
        "\uf0ac": "←", "\uf0ad": "↑", "\uf0af": "↓",  # Symbol矢印系
    },
    "sysmac": dict(PUA_MAP_COMMON),
}

def map_pua(vendor, text):
    for k, v in PUA_MAP.get(vendor, {}).items():
        if k in text: text = text.replace(k, v)
    return text

PUA = re.compile(r"[\ue000-\uf8ff]")

def postprocess(vendor, parts):
    out, buf_num = [], None
    for kind, text in parts:
        if kind == "p" and re.fullmatch(r"\d{1,2}", text.strip()):
            buf_num = text.strip(); continue
        if buf_num and kind == "p":
            text = f"{buf_num}. {text}"; buf_num = None
        elif buf_num:
            out.append(("p", f"{buf_num}.")); buf_num = None
        out.append((kind, text))
    res = []
    for kind, text in out:
        if kind == "img":
            res.append((kind, text)); continue
        text = map_pua(vendor, text)
        if vendor == "gxworks3":
            text = text.replace("，", "、").replace("．", "。")
            text = re.sub(r"[\ue000-\uf8ff]\s*(\d+)ページ\s*", "→ ", text)
            text = re.sub(r"\(?(\d+)ページ\s+", "→ ", text)
        elif vendor == "sysmac":
            text = re.sub(r"\s*[（(]P\.[0-9A-Za-z\-]+[）)]", "", text)
            text = re.sub(r"^l\s+", "- ", text)
        elif vendor == "kvstudio":
            text = re.sub(r"[（(]\s*\d+ページ\s*[）)]", "", text)
            text = re.sub(r"「?\d+ページ\s+", "→ ", text)
        text = PUA.sub("", text)
        text = re.sub(r"[ \t]+", lambda m: " ", text).strip()
        if not text: continue
        if kind == "p":
            for mark, rep in VENDORS[vendor]["bullet_map"].items():
                if text.startswith(mark) and mark != "■":
                    text = rep + text[len(mark):].strip(); break
            if text.startswith("■"):
                t = text[1:].strip()
                text = f"**{t}**" if len(t) < 60 else t
        text = re.sub(r"→ *→ *", "→ ", text)
        text = re.sub(r"[・.]{3,}", " ", text).strip()
        if not text: continue
        if kind == "p" and text.count("•") >= 2:
            items = [x.strip() for x in text.split("•") if x.strip()]
            if items and len(text) - len(items[0]) > 4:
                for x in items:
                    res.append(("p", "- " + x))
                continue
        text = re.sub(r"^•\s*", "- ", text)
        res.append((kind, text))
    # 折返しで分断された段落を結合
    merged = []
    for kind, text in res:
        if (merged and kind == "p" and merged[-1][0] == "p"):
            prev = merged[-1][1]
            if (len(prev) >= 8 and not prev.endswith(("。", "！", "？", "：", "」", "）", ")", ">", "*"))
                    and re.match(r"[\u3040-\u30ff\u4e00-\u9fff、]", prev[-1])
                    and re.match(r"[\u3040-\u30ff\u4e00-\u9fff（「]", text[:1])
                    and not text.startswith(("- ", "**"))):
                merged[-1] = ("p", prev + text)
                continue
        merged.append((kind, text))
    return merged

def to_markdown(vendor, cfg, unit, parts):
    lines = ["---",
             f'vendor: {vendor}',
             f'vendor_label: "{cfg["label"]} ({cfg["company"]})"',
             f'id: "{unit["slug"]}"',
             f'num: "{unit["num"]}"',
             f'title: "{unit["title"]}"',
             f'category: {unit["cat"]}',
             f'source: "{cfg["manual"]} pp.{unit["page"]}-{unit["page_end"]}"',
             "---", "",
             f'# {unit["num"]} {unit["title"]}', ""]
    prev = None
    for kind, text in parts:
        if kind == "h":
            lines += ["", text, ""]
        elif kind in ("table", "img"):
            lines += ["", text.rstrip(), ""]
        else:
            if prev == "p": lines.append("")
            lines.append(text)
        prev = kind
    md = "\n".join(lines)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md + "\n"

# ---------------------------------------------------------------- main
def main():
    import sys, gc
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(OUT, exist_ok=True)
    catalog = []
    for vendor, cfg in VENDORS.items():
        if only and vendor != only: continue
        doc = fitz.open(cfg["file"])
        toc = doc.get_toc()
        units, breaks = BUILDERS[vendor](toc)
        os.makedirs(f"{OUT}/{vendor}", exist_ok=True)
        print(f"== {vendor}: {len(units)} units")
        for i, u in enumerate(units):
            if i and i % 20 == 0:
                doc.close(); gc.collect(); doc = fitz.open(cfg["file"])
                print(f"  ...{i}/{len(units)}", flush=True)
            u["slug"] = slug_num(u["num"])
            u["_vendor"] = vendor
            u["_figseq"] = 1
            if os.path.exists(f"{OUT}/{vendor}/{u['slug']}.md"):
                continue  # レジューム: 生成済みはスキップ
            nxt = units[i+1] if i+1 < len(units) else None
            end = (nxt["page"] if nxt else doc.page_count)
            nb = [b for b in breaks if b > u["page"]]
            if nb: end = min(end, nb[0] - 1 if nb[0] < end else end)
            u["page_end"] = max(end, u["page"])
            # ユニット内サブ見出し(TOCの深い階層)
            subs = []
            for lv, t, pg in toc[u["toc_i"]+1:]:
                if pg >= u["page_end"] and pg > u["page"]: break
                if lv > toc[u["toc_i"]][0]:
                    rel = lv - toc[u["toc_i"]][0] + 1
                    subs.append((min(rel,4), t, pg))
                elif lv <= toc[u["toc_i"]][0]:
                    break
            parts, ok = render_unit(doc, cfg, u, nxt, subs)
            parts = postprocess(vendor, parts)
            md = to_markdown(vendor, cfg, u, parts)
            path = f"{OUT}/{vendor}/{u['slug']}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            catalog.append(dict(vendor=vendor, slug=u["slug"], num=u["num"],
                                title=u["title"], cat=u["cat"],
                                chars=len(md), started=ok,
                                pages=f'{u["page"]}-{u["page_end"]}'))
        doc.close()
        with open(f"/home/claude/work/catalog_{vendor}.json", "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=1)
    # 統計
    from collections import Counter
    print(Counter((c["vendor"]) for c in catalog))
    print("title未検出:", [f'{c["vendor"]}/{c["num"]}' for c in catalog if not c["started"]][:20])
    print("極小ユニット:", [f'{c["vendor"]}/{c["num"]}({c["chars"]})' for c in catalog if c["chars"]<400][:20])

if __name__ == "__main__":
    main()
