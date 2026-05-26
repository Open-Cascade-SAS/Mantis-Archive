#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Iterable
from urllib.parse import quote


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"}
PLACEHOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360" role="img" aria-label="Attachment omitted">
  <rect width="640" height="360" fill="#eef3f8"/>
  <rect x="40" y="40" width="560" height="280" rx="18" fill="#ffffff" stroke="#b9c8d8" stroke-width="4"/>
  <path d="M170 235h300" stroke="#5d7286" stroke-width="12" stroke-linecap="round"/>
  <path d="M210 120h220v80H210z" fill="#dce7f1" stroke="#8aa0b5" stroke-width="4"/>
  <circle cx="260" cy="160" r="16" fill="#8aa0b5"/>
  <path d="M320 148l34 40 24-26 52 58H260z" fill="#8aa0b5"/>
  <text x="320" y="282" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" fill="#33475b">Attachment omitted from GitHub Pages copy</text>
</svg>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--image-max-bytes", type=int, default=1_500_000)
    parser.add_argument("--file-max-bytes", type=int, default=100_000)
    return parser.parse_args()


def attachment_redirect_html(release_tag: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Attachment Not Published On Pages</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: #ffffff;
      --line: #c8d5e2;
      --text: #16324a;
      --muted: #587188;
      --accent: #0d6aa8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, #edf4fb 0%, var(--bg) 100%);
      color: var(--text);
      font: 16px/1.5 Arial, sans-serif;
      padding: 24px;
    }}
    main {{
      max-width: 720px;
      width: 100%;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 14px 40px rgba(25, 55, 87, 0.08);
    }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    p {{ margin: 0 0 14px; color: var(--muted); }}
    code {{
      background: #eef3f8;
      border-radius: 6px;
      padding: 2px 6px;
      color: var(--text);
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Attachment not published on GitHub Pages</h1>
    <p>The GitHub Pages copy keeps only small files and small images.</p>
    <p>The attachment <code id="file-name">attachment</code> for ticket <code id="ticket-ref">ticket</code> was omitted from the web copy to keep the published site lightweight.</p>
    <p>The full archive remains available in the release package for <code>{html.escape(release_tag)}</code>.</p>
    <p><a href="javascript:history.back()">Go back</a></p>
  </main>
  <script>
    const params = new URLSearchParams(window.location.search);
    const file = params.get("file");
    const ticket = params.get("ticket");
    if (file) document.getElementById("file-name").textContent = file;
    if (ticket) document.getElementById("ticket-ref").textContent = "#" + ticket.padStart(5, "0");
  </script>
</body>
</html>
"""


def replace_many(text: str, removed_files: Iterable[str], ticket_slug: str, release_tag: str) -> str:
    for file_name in removed_files:
        omitted_href = (
            f"../../attachment-omitted.html"
            f"?ticket={quote(ticket_slug)}&file={quote(file_name)}&release={quote(release_tag)}"
        )
        text = text.replace(
            f'href="attachments/{file_name}"',
            f'href="{omitted_href}" data-omitted-attachment="1"',
        )
        text = text.replace(
            f'src="attachments/{file_name}"',
            'src="../../assets/attachment-omitted.svg" data-omitted-attachment="1"',
        )
    return text


def main() -> None:
    args = parse_args()
    site_root = Path(args.site_root).resolve()
    tickets_root = site_root / "tickets"
    assets_root = site_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    (assets_root / "attachment-omitted.svg").write_text(PLACEHOLDER_SVG, encoding="utf-8")

    removed_by_ticket: dict[str, list[str]] = {}

    for attachment in tickets_root.glob("*/attachments/*"):
        if not attachment.is_file():
            continue
        size = attachment.stat().st_size
        ext = attachment.suffix.lower()
        keep = False
        if ext in IMAGE_EXTENSIONS:
            keep = size <= args.image_max_bytes
        else:
            keep = size <= args.file_max_bytes
        if keep:
            continue
        ticket_slug = attachment.parent.parent.name
        removed_by_ticket.setdefault(ticket_slug, []).append(attachment.name)
        attachment.unlink()

    for ticket_slug, removed_names in removed_by_ticket.items():
        ticket_html = tickets_root / ticket_slug / "index.html"
        if not ticket_html.exists():
            continue
        text = ticket_html.read_text(encoding="utf-8", errors="ignore")
        rewritten = replace_many(text, removed_names, ticket_slug, args.release_tag)
        ticket_html.write_text(rewritten, encoding="utf-8")

    redirect_page = site_root / "attachment-omitted.html"
    redirect_page.write_text(
        attachment_redirect_html(args.release_tag),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
