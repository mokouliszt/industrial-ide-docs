#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Industrial IDE DocsのMarkdownを静的検査する。"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONTENT = REPO / "public" / "content"
PUBLIC = REPO / "public"
VENDORS = ("gxworks3", "kvstudio", "sysmac")


def field(frontmatter: str, name: str) -> str | None:
    match = re.search(rf'^{re.escape(name)}:\s*"?([^"\n]+)"?\s*$', frontmatter, re.M)
    return match.group(1).strip() if match else None


def pipe_count(line: str) -> int:
    return len(re.findall(r"(?<!\\)\|", line)) - 1


def audit_file(path: Path) -> tuple[list[str], Counter[str], int, int]:
    errors: list[str] = []
    warnings: Counter[str] = Counter()
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return [f"{path}: invalid UTF-8 ({exc})"], warnings, 0, 0

    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        return [f"{path}: frontmatter is missing or malformed"], warnings, 0, 0
    frontmatter, body = match.groups()

    vendor = field(frontmatter, "vendor")
    required = ("vendor", "id", "title", "category", "source")
    if vendor != "common":
        required += ("num",)
    for key in required:
        if field(frontmatter, key) is None:
            errors.append(f"{path}: frontmatter field '{key}' is missing")

    num, title = field(frontmatter, "num"), field(frontmatter, "title")
    h1s = re.findall(r"^# (.+)$", body, re.M)
    if len(h1s) != 1:
        errors.append(f"{path}: expected exactly one H1, found {len(h1s)}")
    elif title:
        expected = f"{num} {title}" if num else title
        if h1s[0] != expected:
            errors.append(f"{path}: H1 does not match frontmatter ({h1s[0]!r})")

    if "�" in text:
        errors.append(f"{path}: contains a Unicode replacement character")
    if re.search(r"[\ue000-\uf8ff]", text):
        errors.append(f"{path}: contains an unmapped private-use glyph")
    if re.search(r"\]\(\s*\)", text):
        errors.append(f"{path}: contains an empty Markdown link")
    for label, target in re.findall(r"(?<!!)\[([^\]\n]+)\]\(([^)\n]*)\)", body):
        target = target.strip()
        if re.match(r"^(?:https?://|mailto:|#)", target):
            continue
        if re.fullmatch(
            r"/(?:gxworks3|kvstudio|sysmac|common)/[a-z0-9-]+/?(?:#[^\s]+)?",
            target,
        ):
            continue
        if re.fullmatch(r"(?:\.\./)*[a-z0-9_./-]+\.md(?:#[^\s]+)?", target):
            continue
        errors.append(
            f"{path}: suspicious Markdown link [{label}]({target}); "
            "use full-width parentheses for literal UI notation"
        )
    if re.search(r"\[[^\]\n]*\n\s*\n!\[", body):
        errors.append(f"{path}: a UI label is split by a figure")
    if re.search(r"^#{2,6}\s+[・•●■]", body, re.M):
        errors.append(f"{path}: contains a bullet marker at the start of a heading")
    if re.search(
        r"^(?:ポイント|参考|注意|注意事項|使用上の注意|重要|警告|画面表示|表示内容)$",
        body,
        re.M,
    ):
        errors.append(f"{path}: contains an unformatted standalone label")

    lines = body.splitlines()
    table_count = 0
    index = 0
    while index < len(lines):
        if not lines[index].startswith("|"):
            index += 1
            continue
        start = index
        table: list[str] = []
        while index < len(lines) and lines[index].startswith("|"):
            table.append(lines[index])
            index += 1
        table_count += 1
        widths = [pipe_count(line) for line in table]
        separator_ok = len(table) >= 2 and re.fullmatch(
            r"\|(?:\s*:?-+:?\s*\|)+", table[1]
        )
        if len(table) < 2 or len(set(widths)) != 1 or not separator_ok:
            errors.append(
                f"{path}:{start + 1}: malformed table (column counts={widths[:8]})"
            )

    image_count = 0
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
        image_count += 1
        if re.match(r"^(?:https?:)?//", image):
            continue
        target = PUBLIC / image.lstrip("/")
        if not target.is_file():
            errors.append(f"{path}: missing image: {image}")

    if body.count("```") % 2:
        errors.append(f"{path}: unclosed fenced code block")

    previous = None
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped and previous == stripped and not stripped.startswith(("|", "---")):
            warnings["consecutive duplicate line"] += 1
        previous = stripped if stripped else None
        if re.match(r"^(?:ジ[）)]|ページ[）)]|ださい。|択$|」$)", stripped):
            warnings["detached line fragment"] += 1
        if re.search(r"(?:ペー|参照してく)$", stripped):
            warnings["truncated line ending"] += 1

    editorial_patterns = {
        "manual self-reference": r"本書|本マニュアル|本取扱説明書",
        "manual-style introduction": r"(?:本章|本節)では.{0,100}(?:説明|解説)します",
        "ornamental product brackets": r"[《》≪≫]",
        "raw bullet glyph": r"•",
    }
    for label, pattern in editorial_patterns.items():
        warnings[label] += len(re.findall(pattern, body))

    return errors, warnings, table_count, image_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=CONTENT)
    args = parser.parse_args()

    paths = [
        path
        for vendor in (*VENDORS, "common")
        for path in sorted((args.root / vendor).glob("*.md"))
    ]
    all_errors: list[str] = []
    all_warnings: Counter[str] = Counter()
    tables = images = 0
    for path in paths:
        errors, warnings, file_tables, file_images = audit_file(path)
        all_errors.extend(errors)
        all_warnings.update(warnings)
        tables += file_tables
        images += file_images

    print(f"files={len(paths)} tables={tables} image-references={images}")
    if all_warnings:
        print("warnings:")
        for label, count in sorted(all_warnings.items()):
            if count:
                print(f"  {label}: {count}")
    if all_errors:
        print(f"errors={len(all_errors)}")
        for error in all_errors:
            print(f"  {error}")
        return 1
    print("errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
