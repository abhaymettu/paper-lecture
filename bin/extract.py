#!/usr/bin/env python3
"""Pull text and figures (with captions) out of a paper so a lesson can be written from it.

Usage: extract.py <paper.pdf> [outdir]
Writes <outdir>/text.md, <outdir>/figNN.png, <outdir>/figures.json

Figures are found by clustering the non-text ink on each page and giving every
caption its nearest cluster. Captions sit above, below, or beside their artwork
depending on the journal, so anything directional gets it wrong somewhere.
"""
import json
import math
import os
import re
import sys

import fitz

CAPTION = re.compile(r"^\s*(Fig(?:ure|\.)?|Table)\s*\.?\s*(\d+)", re.I)
DPI = 200
GAP = 18          # pt; ink closer than this is part of the same figure
PAD = 5           # pt of breathing room around the final crop


def captions(page):
    out = []
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        m = CAPTION.match(text)
        if m:
            out.append({
                "kind": m.group(1).lower().rstrip("."),
                "num": m.group(2),
                "rect": fitz.Rect(x0, y0, x1, y1),
                "caption": " ".join(text.split())[:600],
            })
    return out


def ink(page):
    """Non-text marks on the page, minus page furniture."""
    pr = page.rect
    page_area = pr.get_area()
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") == 1:
            out.append(fitz.Rect(b["bbox"]))
    for d in page.get_drawings():
        out.append(fitz.Rect(d["rect"]))

    keep = []
    for r in out:
        r = r & pr
        if r.is_empty or r.width < 4 or r.height < 4:
            continue
        if r.get_area() > 0.6 * page_area:          # full-page frame or background
            continue
        if r.width < 26 and r.height > 0.4 * pr.height:   # sidebar stamp ("Downloaded at...")
            continue
        if r.height < 26 and r.width > 0.9 * pr.width:    # header/footer rule
            continue
        keep.append(r)
    return keep


def cluster(rects, gap=GAP):
    """Merge rects that touch or nearly touch, repeatedly, until stable."""
    groups = list(rects)
    changed = True
    while changed:
        changed = False
        out = []
        for r in groups:
            hit = None
            for i, c in enumerate(out):
                if (c + (-gap, -gap, gap, gap)).intersects(r):
                    hit = i
                    break
            if hit is None:
                out.append(fitz.Rect(r))
            else:
                out[hit] |= r
                changed = True
        groups = out
    return groups


def gap_between(a, b):
    dx = max(0.0, a.x0 - b.x1, b.x0 - a.x1)
    dy = max(0.0, a.y0 - b.y1, b.y0 - a.y1)
    return math.hypot(dx, dy)


def table_rect(page, cap):
    """Tables are set as text, so there is no ink to cluster: run from the
    caption down to the next real paragraph."""
    pr, cr = page.rect, cap["rect"]
    hi = pr.y1
    for b in sorted(page.get_text("blocks"), key=lambda b: b[1]):
        if b[1] > cr.y1 + 6 and len(b[4].strip()) > 300 and not CAPTION.match(b[4]):
            hi = b[1] - 4
            break
    r = fitz.Rect(max(pr.x0, cr.x0 - 20), cr.y1 + 2, min(pr.x1, cr.x1 + 20), hi)
    return r if r.height > 40 else None


def assign(page, caps):
    """Give each caption the ink cluster nearest to it, one cluster per caption."""
    blobs = [c for c in cluster(ink(page)) if c.width > 60 and c.height > 40]
    pairs = sorted(
        ((gap_between(c["rect"], b), ci, bi)
         for ci, c in enumerate(caps) for bi, b in enumerate(blobs)),
        key=lambda t: t[0],
    )
    taken_c, taken_b, result = set(), set(), {}
    for dist, ci, bi in pairs:
        if ci in taken_c or bi in taken_b or dist > 120:
            continue
        taken_c.add(ci)
        taken_b.add(bi)
        result[ci] = blobs[bi]
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: extract.py <paper.pdf> [outdir]")
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_extract"
    os.makedirs(out, exist_ok=True)

    doc = fitz.open(src)
    figs, parts = [], []

    for pno, page in enumerate(doc, 1):
        parts.append(f"\n\n<!-- page {pno} -->\n\n" + page.get_text("text"))
        caps = captions(page)
        if not caps:
            continue
        art = assign(page, caps)
        for ci, cap in enumerate(caps):
            if cap["kind"].startswith("tab"):
                r = table_rect(page, cap)
            else:
                r = art.get(ci)
                if r is not None:
                    r = (r + (-PAD, -PAD, PAD, PAD)) & page.rect
            if r is None or r.width < 60 or r.height < 40:
                continue
            name = f"fig{len(figs) + 1:02d}.png"
            pix = page.get_pixmap(clip=r, dpi=DPI)
            pix.save(os.path.join(out, name))
            figs.append({
                "file": name,
                "page": pno,
                "label": f"{cap['kind'].title()} {cap['num']}",
                "caption": cap["caption"],
                "px": [pix.width, pix.height],
            })

    open(os.path.join(out, "text.md"), "w").write("".join(parts))
    json.dump(figs, open(os.path.join(out, "figures.json"), "w"), indent=1)
    print(f"{os.path.basename(src)}: {doc.page_count} pages, {len(figs)} figures -> {out}")
    for f in figs:
        print(f"  {f['file']}  p{f['page']:<3} {f['px'][0]}x{f['px'][1]:<5} {f['caption'][:70]}")


if __name__ == "__main__":
    main()
