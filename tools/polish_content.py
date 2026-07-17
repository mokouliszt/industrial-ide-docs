#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF抽出後のMarkdownを、検索・閲覧向けの技術文書として整形する。

抽出処理そのものでは扱いにくい、節境界の重複、改ページをまたいだ語の
分断、マニュアル固有の装飾ラベルをまとめて補正する。変換は冪等になる
ようにし、CIや再抽出後にも同じ結果を再現できるようにする。
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


CONTENT_ROOT = Path(__file__).resolve().parents[1] / "public" / "content"
VENDORS = ("gxworks3", "kvstudio", "sysmac")
JP = r"\u3040-\u30ff\u3400-\u9fff々〆ヶー"


@dataclass
class MarkdownFile:
    path: Path
    text: str
    source_start: int


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^(---\n.*?\n---\n)(.*)$", text, re.S)
    if not match:
        return "", text
    return match.group(1), match.group(2)


def source_start(text: str) -> int:
    frontmatter, _ = split_frontmatter(text)
    match = re.search(r"\bpp\.(\d+)-\d+", frontmatter)
    return int(match.group(1)) if match else 10**9


def first_text_anchor(body: str) -> str | None:
    """次節の先頭を識別できる、十分に長い本文行を返す。"""
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|", "![", "---")):
            continue
        plain = re.sub(r"[*_`]", "", stripped)
        if len(plain) >= 12:
            return stripped
    return None


def trim_next_section_overlap(files: list[MarkdownFile], dry_run: bool) -> int:
    """前節末尾へ混入した次節の冒頭を、完全一致する本文行から除去する。"""
    changed = 0
    for current, following in zip(files, files[1:]):
        frontmatter, body = split_frontmatter(current.text)
        _, next_body = split_frontmatter(following.text)
        anchor = first_text_anchor(next_body)
        if not anchor:
            continue

        lines = body.splitlines()
        positions = [i for i, line in enumerate(lines) if line.strip() == anchor]
        # 同一文が本節にも現れる可能性があるため、後半にある一致だけを境界とみなす。
        positions = [i for i in positions if i >= max(8, int(len(lines) * 0.52))]
        if not positions:
            continue

        cut = positions[-1]
        body = "\n".join(lines[:cut]).rstrip() + "\n"
        updated = frontmatter + body
        if updated == current.text:
            continue
        changed += 1
        current.text = updated
        if not dry_run:
            current.path.write_text(updated, encoding="utf-8")
        print(f"overlap: {current.path.name} -> {following.path.name}")
    return changed


def normalize_spacing(line: str) -> str:
    """PDFの折返しで混入した、日本語語中の空白だけを除去する。"""
    # 全角・半角の装飾括弧は製品名の表記には不要。
    line = re.sub(r"[《≪]([^》≫]+)[》≫]", r"\1", line)
    line = re.sub(fr"(?<=[{JP}])[ \t\u3000]+(?=[{JP}])", "", line)
    line = re.sub(fr"(?<=[{JP}])[ \t\u3000]+(?=[A-Za-z0-9])", "", line)
    line = re.sub(fr"(?<=[A-Za-z0-9)%+\]])[ \t\u3000]+(?=[{JP}])", "", line)
    line = re.sub(fr"(?<=[{JP}])[ \t\u3000]+(?=[、。）」』】])", "", line)
    line = re.sub(fr"(?<=[（「『【])[ \t\u3000]+(?=[{JP}A-Za-z0-9])", "", line)
    line = re.sub(r"[ \t\u3000]+([、。！？）」』】])", r"\1", line)
    line = line.replace("：：", "：").replace(":：", "：")
    return line.rstrip()


def rewrite_manual_tone(line: str) -> str:
    stripped = line.strip()
    if stripped in {
        "お使いになる前に必ずお読みください。",
        "必ずお読みください。",
    }:
        return ""

    # 節の導入文だけを簡潔なリファレンス調にする。
    match = re.fullmatch(
        r"(?:(?:本章|本節|ここ)では、?)?(.+?)について(?:簡単に)?説明し(?:ます|ています)。",
        stripped,
    )
    if match and not stripped.startswith(("- ", "|")):
        topic = match.group(1).strip("、 ")
        return f"{topic}をまとめます。"

    match = re.fullmatch(r"(.+?)を(?:以下|下記)に一覧で示します。", stripped)
    if match:
        return f"{match.group(1)}の一覧です。"
    match = re.fullmatch(r"(.+?)を(?:以下|下記)に示します。", stripped)
    if match:
        return f"{match.group(1)}は次のとおりです。"

    if re.fullmatch(r"詳細は、?(?:以下|下記)を参照してください。", stripped):
        return "**関連項目**"
    if re.fullmatch(r"操作方法は、?(?:以下|下記)を参照してください。", stripped):
        return "**操作方法の関連項目**"
    match = re.fullmatch(r"(.+?)の詳細は、?(?:以下|下記)を参照してください。", stripped)
    if match:
        return f"**{match.group(1)}の関連項目**"
    match = re.fullmatch(r"(.+?)は、?(?:以下|下記)を参照してください。", stripped)
    if match and len(match.group(1)) <= 42:
        return f"**{match.group(1)}の関連項目**"

    line = line.replace("ご確認ください", "確認してください")
    return line


def normalize_line(line: str, vendor: str) -> str:
    line = normalize_spacing(line)

    # 画像の代替テキストは自然文なので、出典表記の空白を維持する。
    line = line.replace("図(元マニュアルp.", "図(元マニュアル p.")

    heading = re.match(r"^(#{2,6})\s+([■●•・])\s*(.+)$", line)
    if heading:
        line = f"{heading.group(1)} {heading.group(3)}"
    if line.startswith("#"):
        line = re.sub(r"\s+[•●]\s+", " — ", line)

    # 数字と見出し語がPDF上で密着した箇所を補正する。
    if vendor != "common":
        line = re.sub(r"^(#{1,6}\s+)(\d+(?:[.\-]\d+)+)(?=[^\d\s])", r"\1\2 ", line)
        line = re.sub(r"^(#{2,6}\s+)(\d{1,2})\.(?=\S)", r"\1\2. ", line)
        line = re.sub(
            r"^(#{2,6}\s+)(\d{1,2})(?!(?:号機|点|台|個|本|軸|重|次元|ビット|ワード))"
            r"(?=[^\d\s:：.\-])",
            r"\1\2 ",
            line,
        )
        line = re.sub(
            r"^(#{2,6}\s+)(\d{1,2})\s+(?=(?:号機|点|台|個|本|軸|重|次元|ビット|ワード))",
            r"\1\2",
            line,
        )
        line = re.sub(r"^(#{2,6}\s+)(\d+)\s+:[ \t]*([1n])", r"\1\2:\3", line)

    if line.startswith("|"):
        # 表セル中の箇条書き点は、列構造を壊さない区切りに置き換える。
        line = re.sub(r"\s*•\s*", " / ", line)
        return line
    if line.startswith("#"):
        return rewrite_manual_tone(line)

    labels = {
        "ポイント": "**ポイント**",
        "参考": "**参考**",
        "注意": "**注意**",
        "注意事項": "**注意事項**",
        "使用上の注意": "**使用上の注意**",
        "重要": "**重要**",
        "警告": "**警告**",
        "画面表示": "**画面の開き方**",
        "表示内容": "**画面項目**",
        "操作手順": "**操作手順**",
        "別手順": "**別の手順**",
        "例": "**例**",
    }
    if line.strip() in labels:
        return labels[line.strip()]

    return rewrite_manual_tone(line)


def split_blocks(body: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body.splitlines():
        if re.fullmatch(
            r"\*\*(?:ポイント|参考|注意|注意事項|使用上の注意|重要|警告)\*\*:?", line.strip()
        ):
            if current:
                blocks.append(current)
                current = []
            blocks.append([line])
        elif line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def is_plain_paragraph(block: list[str]) -> bool:
    if len(block) != 1:
        return False
    line = block[0].lstrip()
    return not line.startswith(("#", "|", "![", "```", "---"))


def join_detached_suffixes(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    suffix = re.compile(
        r"^(?:ます。|す。|ません。|さい。|ください。|い。|る。|た。|ました。|"
        r"ださい。|となります。|になります。|の場合|択|」|』|）|\)|"
        r"ジ[）)].*|ページ[）)].*|[（(][0-9]+(?:-[0-9]+)?ページ[）)].*|"
        r"[ァ-ヴー]{2,}」を参照してください。|を参照してください。|」を参照してください。)$"
    )
    removed: set[int] = set()
    joins = 0
    for index, block in enumerate(blocks):
        if not is_plain_paragraph(block) or not suffix.fullmatch(block[0].strip()):
            continue
        previous = index - 1
        # 図や抽出位置のずれた注記ラベルを越えて、語尾を元の文へ戻す。
        skipped = 0
        while previous >= 0 and skipped < 2:
            marker = blocks[previous][0].lstrip()
            if marker.startswith("![") or re.fullmatch(
                r"\*\*(?:ポイント|参考|注意|注意事項|使用上の注意|重要|警告)\*\*:?", marker
            ):
                previous -= 1
                skipped += 1
                continue
            break
        if previous < 0:
            continue

        # 表セルの末尾だけが次段落へ落ちた場合は、最終セルへ戻す。
        if all(line.lstrip().startswith("|") for line in blocks[previous]):
            last = blocks[previous][-1].rstrip()
            if last.endswith("|"):
                blocks[previous][-1] = re.sub(
                    r"\s*\|$", block[0].strip() + " |", last
                )
                removed.add(index)
                joins += 1
            continue
        if not is_plain_paragraph(blocks[previous]):
            continue
        prev = blocks[previous][0].rstrip()
        if prev.endswith(("。", "！", "？", "：", ":")):
            continue
        blocks[previous][0] = prev + block[0].strip()
        removed.add(index)
        joins += 1
    return [block for i, block in enumerate(blocks) if i not in removed], joins


def join_embedded_ui_headings(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    """文中のUI名だけが見出し化された三分割を、1段落へ戻す。"""
    removed: set[int] = set()
    joins = 0
    for index in range(1, len(blocks) - 1):
        if index in removed or index - 1 in removed or index + 1 in removed:
            continue
        previous, heading, following = blocks[index - 1], blocks[index], blocks[index + 1]
        if not (is_plain_paragraph(previous) and is_plain_paragraph(following)):
            continue
        if len(heading) != 1:
            continue
        match = re.match(r"^#{2,6}\s+(.+)$", heading[0])
        if not match:
            continue
        label = match.group(1).strip()
        if not (label.startswith(("[", "［", "【", "「")) or label.endswith("タブ")):
            continue
        if previous[0].rstrip().endswith(("。", "！", "？")):
            continue
        if not re.match(r"^(?:が|を|に|の|と|で|は|から|へ|も|選択)", following[0].lstrip()):
            continue
        previous[0] = previous[0].rstrip() + label + following[0].lstrip()
        removed.update((index, index + 1))
        joins += 1
    return [block for i, block in enumerate(blocks) if i not in removed], joins


def join_particle_continuations(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    """段組みや図で分離した助詞始まりの文を、直前の主語へ戻す。"""
    continuation = re.compile(
        r"^(?:では|とは|について|から|ので|は[、,]?|を|が|に|の|と|で|へ|も|"
        r"できません。|できます。|されます。|となります。)"
    )
    removed: set[int] = set()
    joins = 0
    for index, block in enumerate(blocks):
        if index in removed or not is_plain_paragraph(block):
            continue
        current = block[0].lstrip()
        if not continuation.match(current):
            continue

        previous = index - 1
        skipped = 0
        while previous >= 0 and skipped < 2:
            marker = blocks[previous][0].lstrip()
            if marker.startswith("![") or re.fullmatch(
                r"\*\*(?:ポイント|参考|注意|注意事項|使用上の注意|重要|警告)\*\*:?", marker
            ):
                previous -= 1
                skipped += 1
                continue
            break
        if previous < 0:
            continue

        heading = re.match(r"^#{2,6}\s+(.+)$", blocks[previous][0])
        if heading:
            subject = re.sub(r"^\d+(?:[.\-]\d+)*\s+", "", heading.group(1)).strip()
            block[0] = rewrite_manual_tone(subject + current)
            joins += 1
            continue

        if not is_plain_paragraph(blocks[previous]):
            continue
        prior = blocks[previous][0].rstrip()
        if prior.endswith(("。", "！", "？", "：", ":")):
            continue
        blocks[previous][0] = rewrite_manual_tone(prior + current)
        removed.add(index)
        joins += 1
    return [block for i, block in enumerate(blocks) if i not in removed], joins


def expand_inline_bullets(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    """本文段落へ連結した中点箇条書きを通常のMarkdownリストへ戻す。"""
    result: list[list[str]] = []
    changes = 0
    for block in blocks:
        if not is_plain_paragraph(block) or "•" not in block[0]:
            result.append(block)
            continue
        line = block[0]
        pieces = [piece.strip() for piece in line.split("•")]
        if len(pieces) < 2:
            result.append(block)
            continue
        new_blocks: list[list[str]] = []
        if pieces[0]:
            new_blocks.append([pieces[0]])
        for piece in pieces[1:]:
            if piece:
                new_blocks.append([f"- {piece}"])
        result.extend(new_blocks)
        changes += 1
    return result, changes


def remove_empty_callouts(blocks: list[list[str]]) -> tuple[list[list[str]], int]:
    """参照文の途中へ混入し、本文を持たなくなった注記ラベルを除去する。"""
    removed: set[int] = set()
    label = re.compile(
        r"\*\*(?:ポイント|参考|注意|注意事項|使用上の注意|重要|警告)\*\*:?"
    )
    for index, block in enumerate(blocks):
        if len(block) != 1 or not label.fullmatch(block[0].strip()):
            continue
        if index == len(blocks) - 1 or blocks[index + 1][0].lstrip().startswith("#"):
            removed.add(index)
    return [block for i, block in enumerate(blocks) if i not in removed], len(removed)


def polish_body(body: str, vendor: str) -> tuple[str, dict[str, int]]:
    lines = [normalize_line(line, vendor) for line in body.splitlines()]
    body = "\n".join(line for line in lines if line is not None)
    blocks = split_blocks(body)
    blocks, suffix_joins = join_detached_suffixes(blocks)
    blocks, heading_joins = join_embedded_ui_headings(blocks)
    blocks, particle_joins = join_particle_continuations(blocks)
    blocks, bullet_expansions = expand_inline_bullets(blocks)
    blocks, empty_callouts = remove_empty_callouts(blocks)
    result = "\n\n".join("\n".join(block) for block in blocks).rstrip() + "\n"
    return result, {
        "suffix_joins": suffix_joins,
        "heading_joins": heading_joins,
        "particle_joins": particle_joins,
        "bullet_expansions": bullet_expansions,
        "empty_callouts": empty_callouts,
    }


def canonicalize_h1(frontmatter: str, body: str) -> str:
    """本文H1をfrontmatterの節番号・タイトルと常に一致させる。"""
    num_match = re.search(r'^num:\s*"?([^"\n]+)"?\s*$', frontmatter, re.M)
    title_match = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', frontmatter, re.M)
    if not (num_match and title_match):
        return body
    expected = f"# {num_match.group(1).strip()} {title_match.group(1).strip()}"
    return re.sub(r"^# .+$", expected, body, count=1, flags=re.M)


def load_vendor_files(root: Path, vendor: str) -> list[MarkdownFile]:
    files = []
    for path in (root / vendor).glob("*.md"):
        # errors="replace" also repairs a file truncated in the middle of a UTF-8 sequence.
        text = path.read_text(encoding="utf-8", errors="replace")
        files.append(MarkdownFile(path, text, source_start(text)))
    return sorted(files, key=lambda item: (item.source_start, item.path.name))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=CONTENT_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    overlap_count = 0
    all_files: list[tuple[str, MarkdownFile]] = []
    for vendor in VENDORS:
        files = load_vendor_files(args.root, vendor)
        overlap_count += trim_next_section_overlap(files, args.dry_run)
        all_files.extend((vendor, item) for item in files)

    totals = {
        "suffix_joins": 0,
        "heading_joins": 0,
        "particle_joins": 0,
        "bullet_expansions": 0,
        "empty_callouts": 0,
    }
    changed = 0
    for vendor, item in all_files:
        # overlap除去後のメモリ上テキストを使う。
        frontmatter, body = split_frontmatter(item.text)
        polished, stats = polish_body(body, vendor)
        polished = canonicalize_h1(frontmatter, polished)
        updated = frontmatter + "\n" + polished.lstrip("\n")
        for key, value in stats.items():
            totals[key] += value
        if updated != item.text:
            changed += 1
            item.text = updated
            if not args.dry_run:
                item.path.write_text(updated, encoding="utf-8")

    mode = "would update" if args.dry_run else "updated"
    print(
        f"{mode} {changed} files; overlaps={overlap_count}, "
        f"suffixes={totals['suffix_joins']}, headings={totals['heading_joins']}, "
        f"particles={totals['particle_joins']}, "
        f"inline-bullets={totals['bullet_expansions']}, "
        f"empty-callouts={totals['empty_callouts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
