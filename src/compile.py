import argparse
import sys
import re
from pathlib import Path
from typing import Iterable, List

# ------------------------------------------------------------
# Font & regex constants
# ------------------------------------------------------------
# Put your primary dev font first – this defines the cell metrics.
FONT_STACK = (
    "monospace",                # ultimate fallback
)

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
URL_RE = re.compile(
    r"(https?://[^\s<>\"']+|ftp://[^\s<>\"']+|www\.[^\s<>\"']+|[\w\-]+\.[a-zA-Z]{2,}(?:/[^\s<>\"']*)?)"
)
# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def _html_escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _font_css_list() -> str:
    return ", ".join(f'"{f}"' if " " in f else f for f in FONT_STACK)


def _build_css(cell_width: float) -> str:
    # letter‑spacing is positive when >1, negative when <1
    letter_spacing = cell_width - 1.0
    return f"""
body {{
  margin:0; padding:20px; display:flex; justify-content:center;
  min-height:100vh; background:#fff;
}}

.content {{
  font-family: {_font_css_list()};
  font-size:28px; line-height:1em;           /* 1 terminal row per glyph */
  white-space:pre; word-spacing:0;           /* keep grid */
  letter-spacing:{letter_spacing:.4f}em;     /* WezTerm cell_width */
  font-variant-ligatures:none; font-kerning:none;
  -webkit-font-smoothing:none; -moz-osx-font-smoothing:unset;
  text-rendering:optimizeSpeed;
  width:80ch;
}}

@media (max-width:85ch) {{
  .content{{width:100%;max-width:80ch;}}
}}
@media (max-width:768px) {{
  .content{{font-size:20px;}}
}}
"""

# ------------------------------------------------------------
# Core transformation
# ------------------------------------------------------------

def _to_html(src_text: str, title: str, cell_width: float) -> str:
    md_links: List[str] = []

    def _cache_md(m: re.Match[str]) -> str:
        text, url = m.group(1), m.group(2)
        if not url.startswith(("http://", "https://", "ftp://", "mailto:")):
            url = url.lstrip("/") + (".html" if not url.endswith(".html") else "")
        placeholder = f"§§MD{len(md_links)}§§"
        md_links.append(f'<a href="{url}" target="_blank">{text}</a>')
        return placeholder

    processed = MD_LINK_RE.sub(_cache_md, src_text)

    lit_links: List[str] = []

    def _cache_url(m: re.Match[str]) -> str:
        url = m.group(0)
        if "§§MD" in url:
            return url
        href = url if url.startswith(("http://", "https://", "ftp://")) else f"http://{url}"
        placeholder = f"§§LIT{len(lit_links)}§§"
        lit_links.append(f'<a href="{href}" target="_blank">{url}</a>')
        return placeholder

    processed = URL_RE.sub(_cache_url, processed)
    processed = _html_escape(processed)

    for i, link in enumerate(md_links):
        processed = processed.replace(f"§§MD{i}§§", link)
    for i, link in enumerate(lit_links):
        processed = processed.replace(f"§§LIT{i}§§", link)

    css = _build_css(cell_width)
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        f"<title>{title}</title><style>{css}</style></head><body><pre class='content'>{processed}</pre></body></html>"
    )

# ------------------------------------------------------------
# Compile helpers
# ------------------------------------------------------------

def _compile_one(src: Path, dst: Path, *, title: str | None, cw: float) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    html = _to_html(src.read_text("utf-8"), title or src.stem, cw)
    dst.write_text(html, "utf-8")
    print(f"✔ {src.relative_to(src.parent)} → {dst.relative_to(dst.parent)}")


def _compile_dir(src_dir: Path, dst_dir: Path, *, cw: float) -> None:
    md_files: Iterable[Path] = list(src_dir.rglob("*.md")) + list(src_dir.rglob("*.markdown"))
    if not md_files:
        raise FileNotFoundError("No markdown files found.")
    for f in md_files:
        rel = f.relative_to(src_dir).with_suffix(".html")
        _compile_one(f, dst_dir / rel, title=None, cw=cw)

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def _parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compile Markdown/Text to WezTerm‑accurate HTML.")
    p.add_argument("source", help="Input file or directory")
    p.add_argument("destination", help="Output file or directory")
    p.add_argument("--out-dir", metavar="DIR", help="Prefix path for the output")
    p.add_argument("--title", help="Custom title for single‑file mode")
    p.add_argument("--cell-width", type=float, default=1.0, help="WezTerm‑style cell width factor (default 1.0)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse(argv)
    src = Path(args.source).resolve()
    dst = Path(args.destination)
    if args.out_dir:
        dst = Path(args.out_dir) / dst
    dst = dst.resolve()

    if src.is_dir():
        _compile_dir(src, dst, cw=args.cell_width)
    else:
        _compile_one(src, dst, title=args.title, cw=args.cell_width)
    print("Compilation complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
