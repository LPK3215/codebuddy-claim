#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the data flow diagram used in the README.

Purpose
    Writes docs/assets/data-flow.svg, the diagram that explains how the tool
    turns a credential source into claimed rewards. Every text node inside the
    image is English.

Dependencies
    Python standard library only.

Run
    python scripts/visualization/generate_data_flow.py

Output
    docs/assets/data-flow.svg

The endpoint names printed in the third stage are read from CHECK_ENDPOINTS in
codebuddy_claim.py at run time. A constant shared with the code cannot go
stale, unlike a hand copied list.
"""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "codebuddy_claim.py"
OUTPUT = ROOT / "docs" / "assets" / "data-flow.svg"

FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"
MONO = "Consolas, Menlo, Monaco, monospace"

ENDPOINT_BLOCK = re.compile(r"CHECK_ENDPOINTS\s*=\s*\((.*?)\n\)", re.DOTALL)
ENDPOINT_PAIR = re.compile(r'\("([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\)')

STAGES = (
    ("Credentials", ("--data JSON file", "Cockpit Tools store", "AES-256-GCM encrypted")),
    ("Load accounts", ("decrypt and normalize", "numeric id and uid to text", "dedupe, keep newest by iat")),
    ("Check and claim", None),  # filled from the source file
    ("History", ("claim-history.jsonl", "under the user data dir", "rotates past 5 MiB")),
)

BOX_W = 260
BOX_H = 170
BOX_Y = 130
GAP = 40
START_X = 20


def read_endpoints():
    """Return the endpoint paths declared in CHECK_ENDPOINTS, shortest prefix removed."""
    text = SOURCE.read_text(encoding="utf-8")
    block = ENDPOINT_BLOCK.search(text)
    if not block:
        raise SystemExit("CHECK_ENDPOINTS not found in %s" % SOURCE)
    paths = []
    for check_path, claim_path, _label in ENDPOINT_PAIR.findall(block.group(1)):
        paths.extend((check_path, claim_path))
    if not paths:
        raise SystemExit("no endpoints parsed from %s" % SOURCE)
    prefix = os.path.dirname(paths[0]) + "/"
    if not all(path.startswith(prefix) for path in paths):
        prefix = ""
    return prefix, [path[len(prefix):] for path in paths]


def build_svg(prefix, short_paths):
    """Return the full SVG document as a string."""
    stages = []
    for index, (title, lines) in enumerate(STAGES):
        stages.append((title, short_paths if lines is None else lines))

    boxes = []
    arrows = []
    for index, (title, lines) in enumerate(stages):
        x = START_X + index * (BOX_W + GAP)
        boxes.append(
            '  <g transform="translate(%d, %d)">\n'
            '    <rect width="%d" height="%d" rx="14" fill="#0d1729" stroke="#24405e"/>\n'
            '    <rect width="%d" height="4" rx="2" fill="#22d3ee" opacity="0.55"/>\n'
            '    <text x="22" y="40" fill="#f3f6fb" font-size="17" font-weight="600" '
            'font-family="%s">%s</text>\n'
            '    <line x1="22" y1="56" x2="%d" y2="56" stroke="#1e3350"/>\n'
            "%s\n"
            "  </g>"
            % (
                x,
                BOX_Y,
                BOX_W,
                BOX_H,
                BOX_W,
                FONT,
                title,
                BOX_W - 22,
                "\n".join(
                    '    <text x="22" y="%d" fill="%s" font-size="%s" font-family="%s">%s</text>'
                    % (
                        84 + row * 26,
                        "#22d3ee" if lines is short_paths else "#a8bccf",
                        "12" if lines is short_paths else "13",
                        MONO if lines is short_paths else FONT,
                        line,
                    )
                    for row, line in enumerate(lines)
                ),
            )
        )
        if index:
            ax = START_X + index * (BOX_W + GAP) - GAP
            ay = BOX_Y + BOX_H // 2
            arrows.append(
                '  <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2f5a86" stroke-width="2"/>'
                % (ax, ay, ax + GAP - 10, ay)
            )
            arrows.append(
                '  <path d="M%d %d l-11 -6 l0 12 z" fill="#2f5a86"/>'
                % (ax + GAP, ay)
            )

    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-label="codebuddy-claim data flow">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1220"/>
      <stop offset="100%" stop-color="#101b2d"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="420" fill="url(#bg)"/>

  <text x="20" y="58" fill="#f3f6fb" font-size="24" font-weight="600" font-family="{font}">How a claim moves through the tool</text>
  <text x="20" y="88" fill="#7f93a8" font-size="14" font-family="{font}">Accounts are handled one at a time, with a fixed delay between them.</text>

{boxes}

{arrows}

  <rect x="20" y="336" rx="10" width="1160" height="58" fill="#0d1729" stroke="#24405e"/>
  <text x="40" y="360" fill="#7f93a8" font-size="13" font-family="{font}">Every request below is a POST with a Bearer credential and the header X-Client-Platform: web.</text>
  <text x="40" y="382" fill="#22d3ee" font-size="13" font-family="{mono}">paths are relative to {prefix}</text>
</svg>
""".format(
        font=FONT,
        mono=MONO,
        boxes="\n".join(boxes),
        arrows="\n".join(arrows),
        prefix=prefix,
    )


def main():
    prefix, short_paths = read_endpoints()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_svg(prefix, short_paths), encoding="utf-8")
    print("wrote %s (%d endpoints under %s)" % (OUTPUT.relative_to(ROOT), len(short_paths), prefix))


if __name__ == "__main__":
    main()
