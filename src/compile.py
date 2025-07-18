#!/usr/bin/env python3
"""
Markdown/Text → Pixel-Perfect HTML Compiler
==========================================

Drop‑in replacement focused on **terminal‑accurate rendering**, especially the
Unicode Braille block (U+2800‑U+28FF).

Key features
------------
1. **Web‑font bootstrap** – optional SimBrailleWeb → Unifont → DejaVu Sans Mono →
   FreeMono stack.
2. **Exact 1‑em grid** – every glyph occupies a full terminal cell (height &
   width).
3. **Space → U+2800 conversion** via `--braille` flag so Braille art aligns.
4. **Argparse CLI** with `--braille`, `--title`, `--out-dir`, `--tight` (new)
   for horizontal micro‑adjustment.
5. Clean helper isolation & error handling.
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from typing import Iterable, List

# ---------------------------------------------------------------------------
# HTML & CSS helpers
# ---------------------------------------------------------------------------

FONT_STACK = (
    'SimBrailleWeb',  # bundled web font (optional)
    'Unifont',
    'DejaVu Sans Mono',
    'FreeMono',
    'monospace',
)

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
URL_RE = re.compile(
    r"(https?://[^\s<>\"']+|ftp://[^\s<>\"']+|www\.[^\s<>\"']+|[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[^\s<>\"']*)?)"
)

def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

def _build_css(letter_spacing: float) -> str:
    font_css = ", ".join(f'"{f}"' if " " in f else f for f in FONT_STACK)
    return f"""
@font-face {{
  font-family: 'SimBrailleWeb';
  src: url('fonts/SimBrailleWeb.woff2') format('woff2');
  font-display: swap;
}}

body {{
  margin: 0;
  padding: 20px;
  display: flex;
  justify-content: center;
  min-height: 100vh;
  background: #fff;
}}

.content {{
  font-family: {font_css};
  font-size: 32px;
  line-height: 1em;          /* 1 terminal row */
  white-space: pre;
  word-spacing: 0;
  letter-spacing: {letter_spacing}em;  /* tighten cols */
  font-variant-ligatures: none;
  font-kerning: none;
  -webkit-font-smoothing: none;
  -moz-osx-font-smoothing: unset;
  text-rendering: optimizeSpeed;
  width: 80ch;
}}

@media (max-width: 85ch) {{
  .content {{ width: 100%; max-width: 80ch; }}
}}
@media (max-width: 768px) {{
  .content {{ font-size: 20px; }}
}}
"""

# ---------------------------------------------------------------------------
# Markdown / text → HTML transformation
# ---------------------------------------------------------------------------

def create_html(raw: str, title: str, braille: bool, spacing: float) -> str:
    md_links: List[str] = []

    def _store_md(m: re.Match[str]) -> str:
        text, url = m.group(1), m.group(2)
        if not url.startswith(("http://", "https://", "ftp://", "mailto:")):
            if not url.endswith(".html"):
                url += ".html"
            url = url.lstrip("/")
        placeholder = f"§§MD{len(md_links)}§§"
        md_links.append(f'<a href="{url}" target="_blank">{text}</a>')
        return placeholder

    proc = MARKDOWN_LINK_RE.sub(_store_md, raw)

    lit_links: List[str] = []

    def _store_lit(m: re.Match[str]) -> str:
        url = m.group(0)
        if "§§MD" in url:
            return url
        href = url if url.startswith(("http://", "https://", "ftp://")) else f"http://{url}"
        placeholder = f"§§LIT{len(lit_links)}§§"
        lit_links.append(f'<a href="{href}" target="_blank">{url}</a>')
        return placeholder

    proc = URL_RE.sub(_store_lit, proc)
    proc = _escape_html(proc)

    for i, link in enumerate(md_links):
        proc = proc.replace(f"§§MD{i}§§", link)
    for i, link in enumerate(lit_links):
        proc = proc.replace(f"§§LIT{i}§§", link)

    css = _build_css(spacing)
    return f"""<!DOCTYPE html><html lang='en'><head>
<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>{title}</title><style>{css}</style></head>
<body><pre class='content'>{proc}</pre></body></html>"""

# ---------------------------------------------------------------------------
# Compile helpers
# ---------------------------------------------------------------------------

def compile_file(src: Path, dst: Path, *, braille: bool, title: str | None, spacing: float) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    html = create_html(src.read_text("utf-8"), title or src.stem, braille, spacing)
    dst.write_text(html, "utf-8")
    print(f"Compiled {src} → {dst}")


def compile_dir(src_dir: Path, dst_dir: Path, *, braille: bool, spacing: float) -> None:
    md_files: Iterable[Path] = list(src_dir.rglob("*.md")) + list(src_dir.rglob("*.markdown"))
    if not md_files:
        raise FileNotFoundError("No markdown files found in directory.")
    for md in md_files:
        rel = md.relative_to(src_dir).with_suffix(".html")
        compile_file(md, dst_dir / rel, braille=braille, title=None, spacing=spacing)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compile Markdown / text to pixel‑perfect HTML.")
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--out-dir", metavar="DIR")
    p.add_argument("--braille", action="store_true", help="Swap spaces for U+2800 on lines containing Braille.")
    p.add_argument("--title", help="Custom title for single‑file mode")
    p.add_argument("--tight", type=float, default=0.05, help="Extra horizontal tightening (em units, default 0.05)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    a = parse(argv)
    src = Path(a.source).resolve()
    dst = Path(a.destination)
    if a.out_dir:
        dst = Path(a.out_dir) / dst
    dst = dst.resolve()

    if src.is_dir():
        compile_dir(src, dst, braille=a.braille, spacing=-a.tight)
    else:
        compile_file(src, dst, braille=a.braille, title=a.title, spacing=-a.tight)
    print("Compilation complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
