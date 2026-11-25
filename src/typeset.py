"""
Typesetting engine: HarfBuzz shaping + glyph outlines drawn as paths.

Matplotlib places text with FreeType only, so it ignores the fonts' GPOS kerning
and cannot track (letter-space) text: the result is uneven spacing between letters.
Here every string is shaped with HarfBuzz (kerning, ligatures, optional tracking)
and each glyph outline is drawn at its exact position, so the spacing is the one the
type designers intended, identical in the PDF and the PNG.

Coordinates are page pixels with y growing downwards (the page axes are inverted).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

from config import FONT_DIR

WEIGHT = {"regular": 400, "normal": 400, "medium": 500, "semibold": 600, "bold": 800, "extra bold": 800}
FILES: Dict[Tuple[str, int, bool], str] = {
    ("Archivo XCond", 800, False): "ArchivoXCond-ExtraBold.ttf",
    ("Archivo XCond", 600, False): "ArchivoXCond-SemiBold.ttf",
    ("Archivo Exp", 800, False): "ArchivoExp-ExtraBold.ttf",
    ("Archivo", 400, False): "Archivo-Regular.ttf",
    ("Archivo", 600, False): "Archivo-SemiBold.ttf",
    ("Archivo", 800, False): "Archivo-ExtraBold.ttf",
    ("Newsreader Text", 400, False): "NewsreaderText-Regular.ttf",
    ("Newsreader Text", 600, False): "NewsreaderText-SemiBold.ttf",
    ("Newsreader Text", 400, True): "NewsreaderText-Italic.ttf",
    ("Newsreader Display", 500, False): "NewsreaderDisplay-Medium.ttf",
    ("Newsreader Display", 500, True): "NewsreaderDisplay-MediumItalic.ttf",
}
FALLBACK = "Archivo-Regular.ttf"


def resolve(family: str, weight="regular", style="normal") -> str:
    w = WEIGHT.get(weight, weight) if isinstance(weight, str) else int(weight)
    it = style == "italic"
    cands = [k for k in FILES if k[0] == family and k[2] == it] or [k for k in FILES if k[0] == family]
    if not cands:
        return FALLBACK
    return FILES[min(cands, key=lambda k: abs(k[1] - w))]


class _Font:
    def __init__(self, fname: str):
        path = Path(FONT_DIR) / fname
        self.tt = TTFont(str(path))
        self.upem = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.order = self.tt.getGlyphOrder()
        self.gs = self.tt.getGlyphSet()
        os2 = self.tt["OS/2"]
        self.cap = getattr(os2, "sCapHeight", 0) or int(self.upem * 0.7)
        self.xh = getattr(os2, "sxHeight", 0) or int(self.upem * 0.5)
        blob = hb.Blob.from_file_path(str(path))
        self.hb = hb.Font(hb.Face(blob))
        self.hb.scale = (self.upem, self.upem)
        self._paths: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}

    def outline(self, gid: int):
        if gid not in self._paths:
            pen = _MplPen(self.gs)
            self.gs[self.order[gid]].draw(pen)
            v = np.array(pen.verts, float).reshape(-1, 2) if pen.verts else np.zeros((0, 2))
            self._paths[gid] = (v, np.array(pen.codes, np.uint8))
        return self._paths[gid]


class _MplPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.verts: List[Tuple[float, float]] = []
        self.codes: List[int] = []

    def _moveTo(self, p):
        self.verts.append(p)
        self.codes.append(MPath.MOVETO)

    def _lineTo(self, p):
        self.verts.append(p)
        self.codes.append(MPath.LINETO)

    def _curveToOne(self, p1, p2, p3):
        self.verts += [p1, p2, p3]
        self.codes += [MPath.CURVE4] * 3

    def _qCurveToOne(self, p1, p2):
        self.verts += [p1, p2]
        self.codes += [MPath.CURVE3] * 2

    def _closePath(self):
        self.verts.append((0, 0))
        self.codes.append(MPath.CLOSEPOLY)


@lru_cache(maxsize=None)
def font(fname: str) -> _Font:
    return _Font(fname)


def _runs(s: str, fname: str) -> List[Tuple[str, str]]:
    """Split a string into runs by font, falling back for missing glyphs."""
    f = font(fname)
    runs: List[Tuple[str, str]] = []
    for ch in s:
        use = fname if (ord(ch) in f.cmap or ch in "​") else FALLBACK
        if runs and runs[-1][1] == use:
            runs[-1] = (runs[-1][0] + ch, use)
        else:
            runs.append((ch, use))
    return runs


@lru_cache(maxsize=20000)
def shape(s: str, fname: str, track: float = 0.0):
    """Return [(fname, gid, x_units_of_that_font, y, scale_to_em)], total advance in em."""
    out, pen_em = [], 0.0
    for text, fn in _runs(s, fname):
        f = font(fn)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(f.hb, buf, {"kern": True, "liga": True})
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((fn, info.codepoint, pen_em + pos.x_offset / f.upem, pos.y_offset / f.upem))
            pen_em += pos.x_advance / f.upem + track
    if out and track:
        pen_em -= track
    return tuple(out), pen_em


def width(s: str, size: float, family: str, weight="regular", style="normal", track: float = 0.0) -> float:
    return shape(s, resolve(family, weight, style), track)[1] * size


def draw(ax, x: float, y: float, s: str, size: float, color: str, family: str, weight="regular", style="normal",
         ha: str = "left", va: str = "top", track: float = 0.0, linespacing: float = 1.0, zorder: float = 5):
    """Draw text at (x, y) in a y-down pixel axes. va: top (cap height), center, baseline, bottom."""
    fname = resolve(family, weight, style)
    f = font(fname)
    lines = s.split("\n")
    verts, codes = [], []
    for li, line in enumerate(lines):
        glyphs, adv = shape(line, fname, track)
        w = adv * size
        x0 = x - (w if ha == "right" else w / 2 if ha == "center" else 0)
        cap = f.cap / f.upem * size
        base = {"top": y + cap, "center": y + cap / 2, "baseline": y, "bottom": y}.get(va, y + cap)
        base += li * size * linespacing * 1.15
        for fn, gid, gx, gy in glyphs:
            g = font(fn)
            v, c = g.outline(gid)
            if not len(v):
                continue
            sc = size / g.upem
            pts = np.empty_like(v)
            pts[:, 0] = x0 + gx * size + v[:, 0] * sc
            pts[:, 1] = base - gy * size - v[:, 1] * sc
            verts.append(pts)
            codes.append(c)
    if not verts:
        return None
    patch = PathPatch(MPath(np.concatenate(verts), np.concatenate(codes)), fc=color, ec="none", lw=0, zorder=zorder)
    ax.add_patch(patch)
    return patch
