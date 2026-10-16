#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the README banner image.

Purpose
    Writes docs/assets/banner.svg, the banner shown at the top of README.md and
    README.zh-CN.md. Every text node inside the image is English, so the file
    renders identically on every platform and stays clear of font fallbacks.

Dependencies
    Python standard library only.

Run
    python scripts/visualization/generate_banner.py

Output
    docs/assets/banner.svg

The version shown on the banner is read from pyproject.toml at run time, so the
image cannot drift from the packaging metadata.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "pyproject.toml"
OUTPUT = ROOT / "docs" / "assets" / "banner.svg"

FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"
MONO = "Consolas, Menlo, Monaco, monospace"


def read_version():
    """Read the [project] version out of pyproject.toml."""
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("version not found in %s" % VERSION_FILE)
    return match.group(1)


def build_svg(version):
    """Return the full SVG document as a string."""
    rows = (
        ("A", "CLAIMED credit=N", "#22d3ee"),
        ("B", "ALREADY-CLAIMED", "#7dd3a0"),
        ("C", "INACTIVE", "#8b9bb0"),
    )

    row_svg = []
    y = 74
    for name, status, color in rows:
        row_svg.append(
            '    <circle cx="40" cy="%d" r="9" fill="none" stroke="%s" stroke-width="2"/>'
            % (y, color)
        )
        row_svg.append(
            '    <path d="M35 %d l4 4 l8 -9" fill="none" stroke="%s" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"/>' % (y, color)
        )
        row_svg.append(
            '    <text x="64" y="%d" fill="#c9d6e4" font-size="15" font-family="%s">'
            "account %s</text>" % (y + 5, MONO, name)
        )
        row_svg.append(
            '    <text x="196" y="%d" fill="%s" font-size="15" font-family="%s">%s</text>'
            % (y + 5, color, MONO, status)
        )
        y += 42

    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="320" viewBox="0 0 1200 320" role="img" aria-label="codebuddy-claim">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1220"/>
      <stop offset="100%" stop-color="#111d31"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="55%" stop-color="#4f9cf9"/>
      <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="1200" height="320" fill="url(#bg)"/>
  <circle cx="1010" cy="80" r="210" fill="url(#glow)"/>
  <circle cx="180" cy="300" r="170" fill="url(#glow)"/>
  <rect x="0" y="0" width="1200" height="4" fill="url(#edge)"/>

  <text x="72" y="132" fill="#f3f6fb" font-size="56" font-weight="700" font-family="{font}" letter-spacing="-1">codebuddy-claim</text>
  <text x="72" y="176" fill="#a8bccf" font-size="21" font-family="{font}">Batch claim CodeBuddy account credits for every account on your machine</text>
  <text x="72" y="210" fill="#6f8299" font-size="16" font-family="{font}">Single file Python CLI  ·  one dependency  ·  credentials opened read-only</text>

  <rect x="72" y="240" rx="13" width="122" height="32" fill="#12263a" stroke="#24405e"/>
  <text x="94" y="261" fill="#22d3ee" font-size="15" font-family="{mono}">v{version}</text>

  <g transform="translate(672, 64)">
    <rect width="456" height="192" rx="16" fill="#0d1729" stroke="#24405e"/>
    <path d="M0 16 A16 16 0 0 1 16 0 H440 A16 16 0 0 1 456 16 V36 H0 Z" fill="#13233a"/>
    <circle cx="24" cy="18" r="5" fill="#ff5f57"/>
    <circle cx="43" cy="18" r="5" fill="#febc2e"/>
    <circle cx="62" cy="18" r="5" fill="#28c840"/>
    <text x="86" y="23" fill="#7f93a8" font-size="13" font-family="{mono}">codebuddy_claim.py claim</text>
    <line x1="0" y1="36" x2="456" y2="36" stroke="#24405e"/>
{rows}
  </g>
</svg>
""".format(
        font=FONT,
        mono=MONO,
        version=version,
        rows="\n".join(row_svg),
    )


def main():
    version = read_version()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_svg(version), encoding="utf-8")
    print("wrote %s (version %s)" % (OUTPUT.relative_to(ROOT), version))


if __name__ == "__main__":
    main()
