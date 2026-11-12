"""
Raster wall detection for line-drawn (double-line) floor-plan images.

Replaces the fragile strip-pairing of the original vectoriser. Pipeline:

  1. tracks      - straight horizontal / vertical drawn lines (sub-pixel position, extent)
  2. bands       - pairs of parallel tracks whose *interior is free of ink*; a band is split
                   wherever ink crosses its interior (wall end caps, window glazing, furniture)
  3. modes       - dominant wall thicknesses from a length-weighted histogram, ranked by how
                   well each thickness forms a connected network (no fixed pixel range)
  4. conflicts   - overlapping candidates resolved by thickness fit and length
  5. healing     - breaks inside one wall line: raster noise, T / X junctions, continuous faces
  6. ends        - every wall must be closed by a cap or a junction at least at one end
                   (furniture parallel to a wall is open at both ends and is rejected)
  7. windows     - >= 3 parallel lines spanning a wall thickness, closed at both ends
  8. network     - walls + windows connected through junctions; isolated groups are reported
  9. gaps        - every remaining gap between two collinear wall pieces is classified
                     window   : glazing lines inside the gap
                     door     : door-swing arc found at a jamb
                     opening  : no wall linework across the gap (intentional)
                     repaired : both wall faces continue across the gap
                     uncertain: partial evidence -> left OPEN and reported for review
 10. corner-flush doors (wall end facing a perpendicular wall with a door swing)

All geometry is kept in pixel space here; `image_importer` converts to millimetres.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
#  data
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Track:
    o: str          # 'H' (pos = row y, s/e = x) | 'V' (pos = column x, s/e = y)
    pos: float
    s: float
    e: float

    @property
    def length(self) -> float:
        return self.e - self.s


@dataclass
class Band:
    o: str
    p1: float       # first face line position (px)
    p2: float       # second face line position (px)
    s: float        # extent along the wall (px)
    e: float
    src: str = 'paired'
    comp: int = -1
    id: int = -1
    term: Tuple[str, str] = ('?', '?')      # how the drawing closes the start / end of the band

    @property
    def d(self) -> float:
        return self.p2 - self.p1

    @property
    def mid(self) -> float:
        return 0.5 * (self.p1 + self.p2)

    @property
    def length(self) -> float:
        return self.e - self.s

    def rect(self, pad: float = 0.0) -> Tuple[float, float, float, float]:
        """(x0, y0, x1, y1) in image pixel coordinates."""
        if self.o == 'H':
            return (self.s - pad, self.p1 - pad, self.e + pad, self.p2 + pad)
        return (self.p1 - pad, self.s - pad, self.p2 + pad, self.e + pad)


@dataclass
class Gap:
    o: str
    p1: float
    p2: float
    s: float
    e: float
    kind: str                       # repaired | window | door | opening | uncertain
    reason: str
    a: int = -1                     # band ids on both sides (-1 for wall / end-to-face)
    b: int = -1
    id: str = ''
    evidence: Dict[str, float] = field(default_factory=dict)

    @property
    def width(self) -> float:
        return self.e - self.s

    def rect(self) -> Tuple[float, float, float, float]:
        if self.o == 'H':
            return (self.s, self.p1, self.e, self.p2)
        return (self.p1, self.s, self.p2, self.e)


@dataclass
class WinRun:
    o: str
    p1: float
    p2: float
    s: float
    e: float
    n_inner: int
    sliding: bool = False
    used: bool = False

    @property
    def mid(self) -> float:
        return 0.5 * (self.p1 + self.p2)

    def rect(self, pad: float = 0.0):
        if self.o == 'H':
            return (self.s - pad, self.p1 - pad, self.e + pad, self.p2 + pad)
        return (self.p1 - pad, self.s - pad, self.p2 + pad, self.e + pad)


# ════════════════════════════════════════════════════════════════════════════
#  1. tracks
# ════════════════════════════════════════════════════════════════════════════
def _tracks(mask: np.ndarray, strength: np.ndarray, o: str, min_len: int) -> List[Track]:
    """Straight lines along rows of `mask` (already oriented so the line direction is +columns)."""
    m = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((1, 3), np.uint8))       # heal 1-px breaks
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((1, min_len), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    raw: List[List[float]] = []
    for k in range(1, n):
        x, y, w, h, _ = st[k]
        sub = (lab[y:y + h, x:x + w] == k)
        if h <= 3:
            wts = (strength[y:y + h, x:x + w] * sub).sum(axis=1) + 1e-6
            pos = y + float((np.arange(h) * wts).sum() / wts.sum())
            raw.append([pos, float(x), float(x + w - 1), float(wts.sum())])
            continue
        for r in range(h):                                  # tall blob: one track per row run
            row = sub[r].astype(np.int8)
            if not row.any():
                continue
            pad = np.concatenate(([0], row, [0]))
            st_i = np.flatnonzero((pad[1:] == 1) & (pad[:-1] == 0))
            en_i = np.flatnonzero((pad[1:] == 0) & (pad[:-1] == 1))
            for a, b in zip(st_i, en_i):
                if b - a >= min_len:
                    raw.append([float(y + r), float(x + a), float(x + b - 1),
                                float(strength[y + r, x + a:x + b].sum())])
    # merge anti-aliased neighbours (rows within 1 px with strong overlap)
    raw.sort(key=lambda t: (t[0], t[1]))
    out: List[List[float]] = []
    for t in raw:
        merged = False
        for q in reversed(out[-12:]):
            if abs(q[0] - t[0]) <= 1.05:
                ov = min(q[2], t[2]) - max(q[1], t[1])
                if ov >= 0.6 * min(q[2] - q[1], t[2] - t[1]):
                    wq, wt = q[3], t[3]
                    q[0] = (q[0] * wq + t[0] * wt) / (wq + wt)
                    q[1], q[2], q[3] = min(q[1], t[1]), max(q[2], t[2]), wq + wt
                    merged = True
                    break
        if not merged:
            out.append(list(t))
    return [Track(o, p, s, e) for p, s, e, _ in out]


# ════════════════════════════════════════════════════════════════════════════
#  2-4. bands, thickness modes, conflicts
# ════════════════════════════════════════════════════════════════════════════
def _interior_rows(p1: float, p2: float) -> Tuple[int, int]:
    return int(math.ceil(p1 + 1.5)), int(math.floor(p2 - 1.5))


def _bands(tracks: List[Track], M: np.ndarray, dmin: float, dmax: float, min_len: float) -> List[Band]:
    tr = sorted(tracks, key=lambda t: t.pos)
    out: List[Band] = []
    for i, a in enumerate(tr):
        for j in range(i + 1, len(tr)):
            b = tr[j]
            d = b.pos - a.pos
            if d > dmax:
                break
            if d < dmin:
                continue
            s0, s1 = int(math.ceil(max(a.s, b.s))), int(math.floor(min(a.e, b.e)))
            if s1 - s0 + 1 < min_len:
                continue
            r0, r1 = _interior_rows(a.pos, b.pos)
            if r1 < r0:
                continue
            ink = M[r0:r1 + 1, s0:s1 + 1].any(axis=0).astype(np.int8)
            pad = np.concatenate(([1], ink, [1]))
            starts = np.flatnonzero((pad[1:] == 0) & (pad[:-1] == 1))
            ends = np.flatnonzero((pad[1:] == 1) & (pad[:-1] == 0))
            for u, v in zip(starts, ends):
                if v - u >= min_len:
                    out.append(Band(a.o, a.pos, b.pos, float(s0 + u), float(s0 + v - 1)))
    return out


def _modes(bands: List[Band]) -> List[float]:
    """Candidate wall thicknesses (px) from a length-weighted histogram of band widths."""
    if not bands:
        return []
    step = 0.5
    hi = max(b.d for b in bands) + 2
    bins = np.zeros(int(hi / step) + 3)
    for b in bands:
        if b.length >= max(3.0 * b.d, 20.0):
            bins[int(round(b.d / step))] += b.length
    if bins.max() <= 0:
        for b in bands:
            bins[int(round(b.d / step))] += b.length
    sm = np.convolve(bins, [1, 2, 3, 2, 1], mode='same')
    peaks = [k for k in range(1, len(sm) - 1) if sm[k] >= sm[k - 1] and sm[k] >= sm[k + 1] and sm[k] > 0]
    peaks.sort(key=lambda k: -sm[k])
    top = sm[peaks[0]] if peaks else 0
    modes: List[float] = []
    for k in peaks:
        if sm[k] < 0.18 * top:
            break
        lo, hi_k = max(0, k - 3), min(len(bins), k + 4)
        w = bins[lo:hi_k]
        c = float((np.arange(lo, hi_k) * w).sum() / max(w.sum(), 1e-9)) * step
        if all(abs(c - m) > 1.6 for m in modes):
            modes.append(c)
        if len(modes) >= 3:
            break
    return modes


def _largest_network(bands: List[Band], tol: float) -> float:
    """Length of the largest group of bands connected through touching rectangles."""
    n = len(bands)
    if n == 0:
        return 0.0
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    R = np.array([b.rect(tol) for b in bands])
    for i in range(n):
        hit = np.flatnonzero((R[i, 0] <= R[:, 2]) & (R[:, 0] <= R[i, 2]) & (R[i, 1] <= R[:, 3]) & (R[:, 1] <= R[i, 3]))
        for j in hit:
            if j > i:
                parent[find(i)] = find(j)
    tot: Dict[int, float] = {}
    for i, b in enumerate(bands):
        r = find(i)
        tot[r] = tot.get(r, 0.0) + b.length
    return max(tot.values())


def _structural_modes(cand: List[Band], modes: List[float]) -> List[float]:
    """
    Order thickness modes by how well their bands form one connected wall network. Glazing,
    furniture outlines and counter edges are frequent but scattered; real walls are connected.
    Modes thinner than 68 % of the main wall thickness (or < 7.0 px) are discarded (not walls).
    """
    scored = []
    for m in modes:
        sel = [b for b in cand if abs(b.d - m) <= max(1.25, 0.13 * m) and b.length >= max(1.4 * m, 8.0)]
        scored.append((_largest_network(sel, max(2.5, 0.6 * m)), m))
    scored.sort(reverse=True)
    main = scored[0][1]
    keep = [main] + [m for s, m in scored[1:] if m >= 0.68 * main and m >= 7.0 and s >= 0.15 * scored[0][0]]
    logger.info("Raster walls: mode network lengths %s -> structural %s",
                [(round(m, 1), round(s)) for s, m in scored], [round(m, 1) for m in keep])
    return keep


def _fit(d: float, modes: List[float]) -> Optional[float]:
    best = None
    for m in modes:
        tol = max(1.25, 0.13 * m)
        if abs(d - m) <= tol and (best is None or abs(d - m) < abs(d - best)):
            best = m
    return best


def _overlap_1d(a0, a1, b0, b1) -> float:
    return min(a1, b1) - max(a0, b0)


def _resolve_conflicts(bands: List[Band], modes: List[float]) -> List[Band]:
    """Same-orientation candidates that overlap in 2D or share a face track with a longer wall: keep the best."""
    def score(b):
        m = _fit(b.d, modes)
        return b.length * (1.0 / (1.0 + abs(b.d - m))) if m is not None else 0.0

    order = sorted(bands, key=lambda b: -score(b))
    kept: List[Band] = []
    for b in order:
        clash = False
        for k in kept:
            if k.o != b.o:
                continue
            ov_s = _overlap_1d(b.s, b.e, k.s, k.e)
            ov_p = _overlap_1d(b.p1, b.p2, k.p1, k.p2)
            if ov_p > 0.5 and ov_s > 2.0:
                clash = True
                break
            # A shorter band sharing one face line with a longer parallel wall is a fixture/wardrobe/counter against it
            if ov_p >= -1.2 and ov_s >= max(2.0, 0.5 * b.length) and k.length > 1.2 * b.length:
                clash = True
                break
        if not clash:
            kept.append(b)
    return kept


# ════════════════════════════════════════════════════════════════════════════
#  helpers on the ink mask
# ════════════════════════════════════════════════════════════════════════════
def _oriented(fg: np.ndarray, o: str) -> np.ndarray:
    return fg if o == 'H' else fg.T


def _interior_ink_cols(M: np.ndarray, p1: float, p2: float, s0: int, s1: int) -> np.ndarray:
    r0, r1 = _interior_rows(p1, p2)
    s0, s1 = max(0, s0), min(M.shape[1] - 1, s1)
    if r1 < r0 or s1 < s0:
        return np.zeros(0, bool)
    return M[r0:r1 + 1, s0:s1 + 1].any(axis=0)


def _face_cover(M: np.ndarray, p: float, s0: int, s1: int) -> float:
    s0, s1 = max(0, s0), min(M.shape[1] - 1, s1)
    if s1 < s0:
        return 1.0
    r = int(round(p))
    rows = M[max(0, r - 1):min(M.shape[0], r + 2), s0:s1 + 1]
    return float(rows.any(axis=0).mean()) if rows.size else 0.0


def _door_arc(fg_d: np.ndarray, o: str, mid: float, s0: float, s1: float, half_t: float = 0.0) -> float:
    """
    Best fraction of a quarter-circle door swing found at either jamb of the gap [s0, s1].
    The hinge may sit on the centre line or on either wall face, and the leaf radius is swept
    finely (0.7 .. 1.1 x gap) because door leaves are drawn slightly narrower than the clear gap.
    """
    g = s1 - s0
    if g < 6:
        return 0.0
    H, W = fg_d.shape
    best = 0.0
    th = np.radians(np.linspace(12, 78, 23))
    cs, sn = np.cos(th), np.sin(th)
    radii = np.arange(0.7 * g, 1.1 * g + 0.01, max(1.0, 0.015 * g))
    for hinge, sgn_s in ((s0, 1.0), (s1, -1.0)):
        for side in (-1.0, 1.0):
            for lat in {0.0, half_t, -half_t}:
                for r in radii:
                    ss = hinge + sgn_s * r * cs
                    pp = mid + lat + side * r * sn
                    xs, ys = (ss, pp) if o == 'H' else (pp, ss)
                    xi, yi = np.round(xs).astype(int), np.round(ys).astype(int)
                    ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
                    if ok.sum() < len(th) * 0.8:
                        continue
                    v = float(fg_d[yi[ok], xi[ok]].mean())
                    if v > best:
                        best = v
                        if best >= 0.95:
                            return best
    return best


def _inner_lines(tracks: List[Track], o: str, p1: float, p2: float, s0: float, s1: float) -> int:
    g = max(s1 - s0, 1.0)
    pos = sorted({round(t.pos, 0) for t in tracks
                  if t.o == o and p1 + 1.2 < t.pos < p2 - 1.2 and _overlap_1d(t.s, t.e, s0, s1) >= 0.7 * g})
    return len(pos)


def _glazing_cover(tracks: List[Track], o: str, p1: float, p2: float, s0: float, s1: float) -> float:
    """Fraction of [s0, s1] covered by lines running inside the wall band (window / sliding panels)."""
    n = int(math.ceil(s1 - s0))
    if n <= 0:
        return 0.0
    on = np.zeros(n, bool)
    for t in tracks:
        if t.o == o and p1 + 1.2 < t.pos < p2 - 1.2 and _overlap_1d(t.s, t.e, s0, s1) > 2:
            on[int(max(0, t.s - s0)):int(min(n, t.e - s0 + 1))] = True
    return float(on.mean())


# ════════════════════════════════════════════════════════════════════════════
#  7. window / sliding-door symbols (>= 3 parallel lines spanning one wall thickness)
# ════════════════════════════════════════════════════════════════════════════
def _window_runs(tracks: List[Track], modes: List[float], t_main: float, fg: np.ndarray) -> List[WinRun]:
    min_run = max(1.5 * t_main, 12.0)
    hole_max = 4.0 * t_main
    out: List[WinRun] = []
    for o in ('H', 'V'):
        M = _oriented(fg, o)
        tr = sorted([t for t in tracks if t.o == o], key=lambda t: t.pos)
        poss = np.array([t.pos for t in tr])
        for a in tr:
            for m in modes:
                tol = max(1.5, 0.15 * m)
                j0, j1 = np.searchsorted(poss, a.pos + m - tol), np.searchsorted(poss, a.pos + m + tol, 'right')
                for j in range(j0, j1):
                    b = tr[j]
                    s0, s1 = max(a.s, b.s), min(a.e, b.e)
                    if s1 - s0 < min_run:
                        continue
                    k0, k1 = np.searchsorted(poss, a.pos + 1.2, 'right'), np.searchsorted(poss, b.pos - 1.2)
                    inner = [tr[k] for k in range(k0, k1) if _overlap_1d(tr[k].s, tr[k].e, s0, s1) > 2]
                    if not inner:
                        continue
                    n = int(math.ceil(s1 - s0)) + 1
                    on = np.zeros(n, bool)
                    for c in inner:
                        u0, u1 = int(max(0, round(c.s - s0))), int(min(n - 1, round(c.e - s0)))
                        on[u0:u1 + 1] = True
                    # bridge short holes (staggered sliding panels) that no jamb line crosses
                    r0, r1 = int(math.ceil(a.pos)), int(math.floor(b.pos))
                    pad = np.concatenate(([1], on.astype(np.int8), [1]))
                    hs = np.flatnonzero((pad[1:] == 0) & (pad[:-1] == 1))
                    he = np.flatnonzero((pad[1:] == 1) & (pad[:-1] == 0))
                    for u, v in zip(hs, he):
                        if u == 0 or v >= n or v - u > hole_max:
                            continue
                        c0, c1 = int(round(s0 + u)), int(round(s0 + v - 1))
                        if r1 > r0 and c1 >= c0 and (M[r0:r1 + 1, c0:c1 + 1].mean(axis=0) >= 0.7).any():
                            continue
                        on[u:v] = True
                    pad = np.concatenate(([0], on.astype(np.int8), [0]))
                    st_i = np.flatnonzero((pad[1:] == 1) & (pad[:-1] == 0))
                    en_i = np.flatnonzero((pad[1:] == 0) & (pad[:-1] == 1))
                    for u, v in zip(st_i, en_i):
                        if v - u < min_run:
                            continue
                        rs, re = s0 + u, s0 + v - 1
                        ins = [c for c in inner if _overlap_1d(c.s, c.e, rs, re) > 2]
                        n_pos = len({round(c.pos) for c in ins})
                        full = [c for c in ins if c.s <= rs + 3 and c.e >= re - 3]
                        sliding = n_pos >= 2 and not full and (re - rs) >= 8 * t_main
                        out.append(WinRun(o, a.pos, b.pos, float(rs), float(re), n_pos, sliding))
    out.sort(key=lambda w: -(w.e - w.s))                    # keep the longest of overlapping duplicates
    kept: List[WinRun] = []
    for w in out:
        if any(k.o == w.o and _overlap_1d(k.p1, k.p2, w.p1, w.p2) > 1.0 and _overlap_1d(k.s, k.e, w.s, w.e) > 2.0
               for k in kept):
            continue
        kept.append(w)
    return kept


# ════════════════════════════════════════════════════════════════════════════
#  6. wall-end terminations
# ════════════════════════════════════════════════════════════════════════════
def _termination(M: np.ndarray, band: Band, at_end: bool, bands: List[Band], t_lo: float, t_hi: float) -> str:
    """
    How the drawing closes this end of a wall band:
      cap      - a line crosses the interior immediately (CAD wall-end / jamb line)
      junction - interior continues into a perpendicular wall and meets its far face
                 (L / T corner), or a perpendicular band starts right there
      glazing  - a parallel line starts inside the interior (window / sliding-door frame)
      edge     - the band runs into the image border (viewport crop)
      open     - nothing closes it (typical of furniture parallel to a wall)
      clutter  - partial ink that fits none of the above
    """
    r0, r1 = _interior_rows(band.p1, band.p2)
    if r1 < r0:
        return 'open'
    step = 1 if at_end else -1
    base = int(round(band.e if at_end else band.s))
    Wm = M.shape[1]
    for k in (1, 2, 3):
        c = base + step * k
        if 0 <= c < Wm and M[r0:r1 + 1, c].mean() >= 0.7:
            return 'cap'
    probe = base + step * 2
    for q in bands:                       # perpendicular band right at this end (tolerant to the corner square)
        if q is band or q.o == band.o:
            continue
        if q.p1 - 2.5 <= probe <= q.p2 + 2.5 and q.s - 0.5 * band.d - 2.5 <= band.mid <= q.e + 0.5 * band.d + 2.5:
            return 'junction'
    if not (0 <= base + step * 3 < Wm):
        return 'edge'
    K = int(round(t_hi + 4))
    cols = [c for c in (base + step * k for k in range(1, K + 1)) if 0 <= c < Wm]
    if len(cols) < K // 2:
        return 'edge'
    prof = np.array([M[r0:r1 + 1, c].mean() for c in cols])
    k_min = max(2, int(0.5 * t_lo))
    for k in range(k_min - 1, len(prof)):
        if prof[k] >= 0.7 and (k == 0 or prof[:k].mean() < 0.25):
            return 'junction'                    # far face of the wall we run into
    sub = M[r0:r1 + 1, min(cols):max(cols) + 1]
    if sub.size and sub.mean(axis=1).max() >= 0.8 and prof.max() < 0.7:
        return 'glazing'
    if prof.mean() < 0.15:
        return 'open'
    return 'clutter'


# ════════════════════════════════════════════════════════════════════════════
#  main entry
# ════════════════════════════════════════════════════════════════════════════
def _same_line(a, b) -> bool:
    return a.o == b.o and abs(a.p1 - b.p1) <= 1.3 and abs(a.p2 - b.p2) <= 1.3


def _line_groups(bands: List[Band], o: str) -> List[List[Band]]:
    groups: List[List[Band]] = []
    for b in sorted([b for b in bands if b.o == o], key=lambda b: (b.mid, b.s)):
        for grp in groups:
            if _same_line(grp[0], b):
                grp.append(b)
                break
        else:
            groups.append([b])
    for g in groups:
        g.sort(key=lambda b: b.s)
    return groups


def _abutting_perpendicular(bands: List[Band], o: str, p1: float, p2: float, g0: float, g1: float) -> bool:
    """A perpendicular wall whose end butts into this gap (T-junction) or passes through it (X)."""
    for q in bands:
        if q.o == o:
            continue
        if q.p1 < g0 - 2.5 or q.p2 > g1 + 2.5:
            continue                               # must fit inside the gap
        if q.e >= p1 - 3.0 and q.s <= p2 + 3.0:    # reaches one of the two faces (or crosses)
            return True
    return False


def _touches(r1, r2) -> bool:
    return r1[0] <= r2[2] and r2[0] <= r1[2] and r1[1] <= r2[3] and r2[1] <= r1[3]


def detect_line_plan(fg: np.ndarray, strength: np.ndarray, *, wall_mm: float = 150.0,
                     mm_per_px: Optional[float] = None, gap_max_mm: float = 3600.0,
                     door_min_mm: float = 600.0) -> Dict:
    """
    Detect walls in a double-line floor-plan raster.
    Returns a dict with bands, windows, gaps, modes, scale and review information (pixels).
    """
    H, W = fg.shape
    min_track = max(6, int(round(min(H, W) / 160.0)))
    tracks = (_tracks(fg, strength, 'H', min_track) +
              _tracks(fg.T.copy(), strength.T.copy(), 'V', min_track))
    th = [t for t in tracks if t.o == 'H']
    tv = [t for t in tracks if t.o == 'V']

    dmax0 = max(18.0, min(48.0, min(H, W) / 25.0))
    cand = (_bands(th, fg, 3.0, dmax0, 6) + _bands(tv, fg.T, 3.0, dmax0, 6))
    modes = _modes(cand)
    if not modes:
        return {'ok': False, 'reason': 'no parallel wall line pairs found', 'tracks': len(tracks)}
    modes = _structural_modes(cand, modes)
    t_main, t_lo, t_max = modes[0], min(modes), max(modes)
    scale = float(mm_per_px) if mm_per_px else wall_mm / t_main
    logger.info("Raster walls: %d tracks, %d candidate bands, thickness modes %s px, scale %.3f mm/px",
                len(tracks), len(cand), [round(m, 1) for m in modes], scale)

    min_len = max(1.1 * t_main, 8.0)
    bands = [b for b in cand if _fit(b.d, modes) is not None and b.length >= min_len]
    # Recover t_main walls whose outer 2-4 px is overlapped by an adjacent wardrobe/fixture frame
    for b in cand:
        if _fit(b.d, modes) is not None or not (0.62 * t_main <= b.d <= 0.85 * t_main and b.length >= 3.0 * t_main):
            continue
        if any(k.o == b.o and _overlap_1d(b.p1, b.p2, k.p1, k.p2) >= -1.5 and _overlap_1d(b.s, b.e, k.s, k.e) > 0.4 * b.length for k in bands):
            continue
        if not any(k.o != b.o and _touches(b.rect(2.5), k.rect(2.5)) for k in bands):
            continue
        ts = _termination(_oriented(fg, b.o), b, False, bands, t_lo, t_max)
        te = _termination(_oriented(fg, b.o), b, True, bands, t_lo, t_max)
        if not (ts in ('cap', 'junction') and te in ('cap', 'junction') and ('junction' in (ts, te))):
            continue
        outer = [t for t in tracks if t.o == b.o and _overlap_1d(t.s, t.e, b.s, b.e) >= 0.35 * b.length and
                 (abs((t.pos - b.p1) - t_main) <= 1.5 or abs((b.p2 - t.pos) - t_main) <= 1.5)]
        if outer:
            t_out = max(outer, key=lambda t: _overlap_1d(t.s, t.e, b.s, b.e))
            p1_new, p2_new = min(b.p1, t_out.pos), max(b.p2, t_out.pos)
            e_new = max(b.e, min(t_out.e, b.e + 1.5 * t_main)) if t_out.e > b.e else b.e
            s_new = min(b.s, max(t_out.s, b.s - 1.5 * t_main)) if t_out.s < b.s else b.s
            bands.append(Band(b.o, p1_new, p2_new, s_new, e_new, src='wardrobe_wall'))
    bands = _resolve_conflicts(bands, modes)
    rejected: List[Dict] = []
    gaps: List[Gap] = []
    fg_d = cv2.dilate(fg, np.ones((3, 3), np.uint8))
    gap_max_px = gap_max_mm / scale
    heal_px = max(2.0, 0.35 * t_main)
    junction_px = 1.6 * t_max + 3.0

    # ── 5. heal breaks inside one wall line: noise, T / X junctions, continuous faces
    def heal_pass() -> bool:
        for o in ('H', 'V'):
            M = _oriented(fg, o)
            for grp in _line_groups(bands, o):
                for a, b in zip(grp, grp[1:]):
                    g0, g1 = a.e, b.s
                    gw = g1 - g0
                    if gw <= 0:                                   # overlapping duplicates on the same line
                        a.e = max(a.e, b.e)
                        bands.remove(b)
                        return True
                    if gw > gap_max_px:
                        continue
                    p1, p2 = 0.5 * (a.p1 + b.p1), 0.5 * (a.p2 + b.p2)
                    c0, c1 = int(round(g0)) + 1, int(round(g1)) - 1
                    ink = _interior_ink_cols(M, p1, p2, c0, c1)
                    empty = ink.size == 0 or not ink.any()
                    fa, fb = _face_cover(M, p1, c0, c1), _face_cover(M, p2, c0, c1)
                    reason = ''
                    if gw <= heal_px:
                        reason = f'{gw:.0f}px break (raster noise / crossing line)'
                    elif gw <= junction_px and _abutting_perpendicular(bands, o, p1, p2, g0, g1):
                        reason = 'T/X junction with a perpendicular wall'
                    elif empty and fa >= 0.9 and fb >= 0.9:
                        reason = 'both wall faces continue across the gap'
                    if reason:
                        gaps.append(Gap(o, p1, p2, g0, g1, 'repaired', reason, -1, -1,
                                        evidence={'face_a': round(fa, 2), 'face_b': round(fb, 2),
                                                  'width_mm': round(gw * scale)}))
                        a.e = b.e
                        a.src = 'healed'
                        bands.remove(b)
                        return True
        return False

    while heal_pass():
        pass

    wins_raw = _window_runs(tracks, modes, t_main, fg)
    anchor_tol = max(3.0, 0.55 * t_main)

    # ── 6. wall-end terminations: a wall must be closed by a cap or a junction at least at one end
    #       (or be a pier between window symbols on an established wall line); short open-ended stubs are furniture
    for b in bands:
        ts = _termination(_oriented(fg, b.o), b, False, bands, t_lo, t_max)
        te = _termination(_oriented(fg, b.o), b, True, bands, t_lo, t_max)
        b.term = (ts, te)
    keep: List[Band] = []
    for b in bands:
        ts, te = b.term
        has_open_end = ('open' in (ts, te) or 'clutter' in (ts, te))
        if has_open_end and b.length < 4.5 * t_main:
            rejected.append({'rect': list(map(float, b.rect())),
                             'why': f'short stub ({b.length * scale:.0f} mm) with open end ({ts}/{te}) - fixture / furniture'})
            continue
        if has_open_end and any(
            k is not b and k.o == b.o and k.length > 1.5 * b.length and
            _overlap_1d(b.s, b.e, k.s, k.e) >= 0.6 * b.length and
            min(abs(b.p1 - k.p2), abs(b.p2 - k.p1)) <= 1.2 * t_main
            for k in bands
        ):
            rejected.append({'rect': list(map(float, b.rect())),
                             'why': f'open-ended band ({ts}/{te}) parallel to a longer structural wall - bed / sofa headboard'})
            continue
        # A short capped box whose only contact with the structure is rubbing its side face against a parallel wall
        # (no perpendicular junction at either end) is a counter / cistern / wardrobe against that wall
        if b.length < 8.5 * t_main and not any(q.o != b.o and _touches(b.rect(3.0), q.rect(3.0)) for q in bands):
            if any(k is not b and k.o == b.o and _overlap_1d(b.p1, b.p2, k.p1, k.p2) >= -2.0 and
                   _overlap_1d(b.s, b.e, k.s - 6.0 * t_main, k.e + 6.0 * t_main) >= 0.5 * b.length for k in bands):
                rejected.append({'rect': list(map(float, b.rect())),
                                 'why': 'short box alongside a parallel wall with no perpendicular junction - counter / fixture'})
                continue
        on_wall_line = any(k is not b and _same_line(b, k) and ('cap' in k.term or 'junction' in k.term) for k in bands)
        win_anchored = (ts == 'glazing' or te == 'glazing') and on_wall_line
        if ts in ('cap', 'junction') or te in ('cap', 'junction') or win_anchored or b.length >= 25.0 * t_main:
            keep.append(b)
        else:
            rejected.append({'rect': list(map(float, b.rect())),
                             'why': f'wall ends not closed ({ts}/{te}) - parallel furniture / glazing, not a wall'})
    bands = keep
    while heal_pass():
        pass

    # ── 7. window / sliding-door symbols closed at BOTH ends by a wall, window or jamb line
    wins = list(wins_raw)

    def alongside_wall(w: WinRun) -> bool:
        """Shares a face line with a parallel wall over most of its length -> furniture against a wall."""
        for b in bands:
            if b.o != w.o or _overlap_1d(b.s, b.e, w.s, w.e) < 0.5 * (w.e - w.s):
                continue
            if abs(b.p2 - w.p1) <= 2.0 or abs(b.p1 - w.p2) <= 2.0 or \
                    _overlap_1d(b.p1, b.p2, w.p1, w.p2) > 0.6 * (w.p2 - w.p1):
                return True
        return False

    def end_closed(w: WinRun, at_end: bool, others: List[WinRun]) -> bool:
        e = w.e if at_end else w.s
        lo, hi = (e - 1.0, e + anchor_tol) if at_end else (e - anchor_tol, e + 1.0)
        box = (lo, w.p1 + 1, hi, w.p2 - 1) if w.o == 'H' else (w.p1 + 1, lo, w.p2 - 1, hi)
        for q in list(bands) + others:
            if q is w:
                continue
            if q.o == w.o and abs(q.mid - w.mid) > 2.5:
                continue                              # parallel but on another line
            if _touches(box, q.rect(anchor_tol if q.o != w.o else 1.5)):
                return True
        M = _oriented(fg, w.o)
        r0, r1 = int(math.ceil(w.p1)), int(math.floor(w.p2))
        for k in (1, 2, 3, 0, -1):
            c = int(round(e)) + (k if at_end else -k)
            if 0 <= c < M.shape[1] and r1 > r0 and M[r0:r1 + 1, c].mean() >= 0.7:
                return True                           # jamb line across the symbol
        return False

    wins = [w for w in wins if not alongside_wall(w)]
    stable = False
    while not stable:
        keep_w = [w for w in wins if end_closed(w, False, wins) and end_closed(w, True, wins)]
        stable = len(keep_w) == len(wins)
        wins = keep_w

    # ── 6b. walls running off the image (viewport crop): trim back to the last junction
    trims: List[Dict] = []
    lim = {'H': W, 'V': H}
    for b in bands:
        for at_end in (False, True):
            edge_hit = (b.e >= lim[b.o] - 3) if at_end else (b.s <= 2)
            if not edge_hit:
                continue
            js = []
            for q in list(bands) + list(wins):
                if q.o == b.o or q is b:
                    continue
                if q.e >= b.p1 - 0.5 * (q.p2 - q.p1) - 3 and q.s <= b.p2 + 0.5 * (q.p2 - q.p1) + 3 and b.s - 3 <= q.mid <= b.e + 3:
                    js.append((q.p1, q.p2))
            if not js:
                continue
            old = (b.s, b.e)
            if at_end:
                b.e = max(p2 for _, p2 in js)
            else:
                b.s = min(p1 for p1, _ in js)
            if b.length < min_len:
                b.s, b.e = old
                continue
            xy = ((old[1] if at_end else old[0]), b.mid)
            xy = xy if b.o == 'H' else (xy[1], xy[0])
            trims.append({'xy': [float(xy[0]), float(xy[1])],
                          'cut_mm': round(abs((old[1] - b.e) if at_end else (b.s - old[0])) * scale),
                          'note': 'wall linework runs off the image - trimmed at its last junction'})

    # ── 8. network: walls + windows connected through junctions; isolated groups are reported
    nodes: List = list(bands) + list(wins)
    n = len(nodes)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tol = max(2.5, 0.35 * t_main)
    R = np.array([q.rect(tol) for q in nodes]) if nodes else np.zeros((0, 4))
    for i in range(n):
        hit = np.flatnonzero((R[i, 0] <= R[:, 2]) & (R[:, 0] <= R[i, 2]) & (R[i, 1] <= R[:, 3]) & (R[:, 1] <= R[i, 3]))
        for j in hit:
            if j > i:
                parent[find(i)] = find(j)
    comps: Dict[int, List[int]] = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    comp_len = {r: sum(nodes[i].e - nodes[i].s for i in m) for r, m in comps.items()}
    biggest = max(comp_len.values()) if comp_len else 0.0
    isolated: List[Dict] = []
    kept: List[Band] = []
    kept_w: List[WinRun] = []
    for r, members in comps.items():
        L = comp_len[r]
        if L >= 0.10 * biggest or L >= 30.0 * t_main:
            kept.extend(nodes[i] for i in members if isinstance(nodes[i], Band))
            kept_w.extend(nodes[i] for i in members if isinstance(nodes[i], WinRun))
        else:
            xs = [nodes[i].rect() for i in members if isinstance(nodes[i], Band)]
            if xs:
                isolated.append({'bands': [list(map(float, x)) for x in xs], 'length_mm': round(L * scale),
                                 'bbox': [min(x[0] for x in xs), min(x[1] for x in xs),
                                          max(x[2] for x in xs), max(x[3] for x in xs)]})
    bands, wins = kept, kept_w
    for k, b in enumerate(bands):
        b.id = k

    # ── 9. remaining gaps along every wall line (between walls and/or window symbols)
    #      -> window / door / opening / repaired / uncertain
    new_wins: List[WinRun] = []
    for o in ('H', 'V'):
        M = _oriented(fg, o)
        for grp in _line_groups(list(bands) + list(wins), o):
            for a, b in zip(grp, grp[1:]):
                g0, g1 = a.e, b.s
                gw = g1 - g0
                if gw <= 0 or gw > gap_max_px:
                    continue
                a_band, b_band = isinstance(a, Band), isinstance(b, Band)
                p1, p2 = 0.5 * (a.p1 + b.p1), 0.5 * (a.p2 + b.p2)
                blocked = any(q.o != o and _overlap_1d(q.p1, q.p2, g0 + 1, g1 - 1) > 1.0 and
                              _overlap_1d(q.s, q.e, p1, p2) > 1.0 for q in bands)
                if blocked:
                    continue                      # a perpendicular wall stands in the gap: not an opening of this line
                c0, c1 = int(round(g0)) + 1, int(round(g1)) - 1
                fa, fb = _face_cover(M, p1, c0, c1), _face_cover(M, p2, c0, c1)
                n_in = _inner_lines(tracks, o, p1, p2, g0, g1)
                glaze = _glazing_cover(tracks, o, p1, p2, g0, g1)
                win_cov = sum(max(0.0, _overlap_1d(w.s, w.e, g0, g1)) for w in wins
                              if w.o == o and abs(w.mid - 0.5 * (p1 + p2)) <= 2.5)
                arc = _door_arc(fg_d, o, 0.5 * (p1 + p2), g0, g1, 0.5 * (p2 - p1))
                cap_a = a_band and a.term[1] == 'cap'
                cap_b = b_band and b.term[0] == 'cap'
                ev = {'inner_lines': n_in, 'window_cover': round(win_cov / max(gw, 1e-6), 2), 'arc': round(arc, 2),
                      'cap_a': int(cap_a), 'cap_b': int(cap_b), 'face_a': round(fa, 2), 'face_b': round(fb, 2),
                      'width_mm': round(gw * scale), 'between': ('wall' if a_band else 'window') + '/' +
                      ('wall' if b_band else 'window')}
                ev['glazing_cover'] = round(glaze, 2)
                if gw <= junction_px and _abutting_perpendicular(list(bands) + list(wins), o, p1, p2, g0, g1):
                    kind, why = 'repaired', 'T/X junction with a perpendicular wall or bay-window return'
                elif fa >= 0.8 and fb >= 0.8 and (n_in >= 1 or glaze >= 0.7) and gw >= 1.5 * t_main:
                    kind, why = 'window', f'continuous window/ventilator symbol ({glaze:.0%} glazing)'
                    for w in wins:
                        if w.o == o and abs(w.mid - 0.5 * (p1 + p2)) <= 2.5 and _overlap_1d(w.s, w.e, g0, g1) > 0.5 * gw:
                            w.used = True
                elif (n_in >= 1 or win_cov >= 0.6 * gw or glaze >= 0.4 or (glaze >= 0.30 and max(fa, fb) >= 0.90)) and gw >= 1.5 * t_main and arc < 0.55:
                    kind, why = 'window', f'glazing lines inside the wall band ({glaze:.0%} of the gap)'
                    for w in wins:
                        if w.o == o and abs(w.mid - 0.5 * (p1 + p2)) <= 2.5 and _overlap_1d(w.s, w.e, g0, g1) > 0.5 * gw:
                            w.used = True
                elif arc >= 0.55:
                    kind, why = 'door', f'door swing arc at the jamb ({arc:.0%} of samples on ink)'
                elif fa < 0.3 and fb < 0.3:
                    kind = 'opening'
                    why = ('no wall linework across the gap; both ends capped' if cap_a and cap_b else
                           'no wall linework across the gap')
                elif fa >= 0.9 and fb >= 0.9:
                    kind, why = 'repaired', 'both wall faces continue (interior clutter ignored)'
                else:
                    kind, why = 'uncertain', 'partial wall linework across the gap - left open for review'
                if kind == 'window' and not (a_band and b_band):
                    new_wins.append(WinRun(o, p1, p2, g0, g1, n_in))      # glazing continues between symbols
                gaps.append(Gap(o, p1, p2, g0, g1, kind, why, a.id if a_band else -1, b.id if b_band else -1,
                                evidence=ev))
    wins.extend(new_wins)
    next_id = max([b.id for b in bands] + [-1]) + 1
    for g in [g for g in gaps if g.kind == 'repaired' and g.evidence.get('between')]:   # apply the late repairs
        a = next((x for x in bands if x.id == g.a), None) if g.a >= 0 else None
        b = next((x for x in bands if x.id == g.b), None) if g.b >= 0 else None
        if a is not None and b is not None and a is not b:
            a.e = max(a.e, b.e)
            a.src = 'healed'
            a.term = (a.term[0], b.term[1])
            bands.remove(b)
            for g2 in gaps:
                if g2.a == b.id:
                    g2.a = a.id
                if g2.b == b.id:
                    g2.b = a.id
        elif a is not None:
            a.e = g.e
            a.src = 'healed'
        elif b is not None:
            b.s = g.s
            b.src = 'healed'
        else:                                   # wall between two window symbols
            nb = Band(g.o, g.p1, g.p2, g.s, g.e, src='healed', id=next_id, term=('glazing', 'glazing'))
            next_id += 1
            bands.append(nb)

    # ── 10. corner-flush doors (free wall end facing another wall with a door swing) & dangling ends
    def end_touches(b: Band, at_end: bool) -> bool:
        e = b.e if at_end else b.s
        lo, hi = (e - 0.5 * b.d, e + 2.0) if at_end else (e - 2.0, e + 0.5 * b.d)
        box = (lo, b.p1, hi, b.p2) if b.o == 'H' else (b.p1, lo, b.p2, hi)
        return any(q is not b and _touches(box, q.rect(1.5)) for q in list(bands) + list(wins))

    taken = ({(g.a, 'e') for g in gaps if g.kind != 'repaired'} |
             {(g.b, 's') for g in gaps if g.kind != 'repaired'})
    dangling: List[Dict] = []
    for b in bands:
        for at_end in (False, True):
            term = b.term[1] if at_end else b.term[0]
            if (b.id, 'e' if at_end else 's') in taken or end_touches(b, at_end):
                continue
            best = None
            for q in bands:
                if q is b:
                    continue
                if q.o == b.o:
                    if _overlap_1d(q.p1, q.p2, b.p1, b.p2) <= 0.5 * b.d:
                        continue
                    lo, hi = q.s, q.e
                else:
                    if _overlap_1d(q.s, q.e, b.p1, b.p2) < 0.5 * b.d:
                        continue
                    lo, hi = q.p1, q.p2
                dist = (lo - b.e) if at_end else (b.s - hi)
                if dist > 0.5 and (best is None or dist < best[0]):
                    best = (dist, q)
            pt = b.e if at_end else b.s
            xy = (pt, b.mid) if b.o == 'H' else (b.mid, pt)
            if best is not None and best[0] <= gap_max_px:
                dist, q = best
                g0, g1 = (b.e, b.e + dist) if at_end else (b.s - dist, b.s)
                arc = _door_arc(fg_d, b.o, b.mid, g0, g1, 0.5 * b.d)
                if arc >= 0.55 and dist * scale >= 0.6 * door_min_mm:
                    gaps.append(Gap(b.o, b.p1, b.p2, g0, g1, 'door', 'corner-flush door swing',
                                    b.id if at_end else -1, -1 if at_end else b.id,
                                    evidence={'arc': round(arc, 2), 'width_mm': round(dist * scale)}))
                    continue
                if term == 'cap':
                    continue                         # capped end facing a wall: opening, decided downstream
                if dist <= junction_px:
                    dangling.append({'xy': [float(xy[0]), float(xy[1])], 'band': b.id, 'term': term,
                                     'note': f'stops {dist * scale:.0f} mm short of a wall (junction repaired later)'})
                    continue
            if term not in ('cap', 'junction', 'edge'):
                dangling.append({'xy': [float(xy[0]), float(xy[1])], 'band': b.id, 'term': term,
                                 'note': 'wall end not closed by a cap or junction'})

    counters: Dict[str, int] = {}
    for g in gaps:
        counters[g.kind] = counters.get(g.kind, 0) + 1
        g.id = f"{g.kind[:3].upper()}_{counters[g.kind]:02d}"

    logger.info("Raster walls: %d bands, %d windows, gaps %s, %d rejected, %d isolated, %d trimmed, %d dangling",
                len(bands), len(wins), counters, len(rejected), len(isolated), len(trims), len(dangling))
    return {
        'ok': True, 'bands': bands, 'windows': wins, 'gaps': gaps, 'modes': modes, 't_main': t_main,
        'scale': scale, 'tracks': tracks, 'isolated': isolated, 'rejected': rejected, 'trimmed': trims,
        'dangling': dangling, 'shape': (H, W),
    }
