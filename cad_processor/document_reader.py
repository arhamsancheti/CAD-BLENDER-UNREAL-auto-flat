"""Word document reader (.docx / .docm / .doc / .rtf / .odt).

Reads a project document the way an architect would and turns it into model inputs:

  1. the floor-plan drawing      - embedded CAD files (DXF / DWG) or the best plan-like picture
                                   (PNG / JPG / EMF / WMF ...) found in the document
  2. the written specification   - wall height, external / internal wall thickness, door size and
                                   head height, window sill / height, ventilator size, lintel level,
                                   slab thickness, skirting height
  3. the room schedule           - room names with their sizes (W x L in m / mm / ft-in, or area),
                                   from paragraphs, lists and tables

No third-party Word library is needed: .docx is read directly from its XML. Legacy formats
(.doc / .rtf / .odt) are converted to .docx with Microsoft Word (COM) or LibreOffice first.
"""
import io
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DOC_EXTS = ('.docx', '.docm', '.dotx', '.doc', '.rtf', '.odt')
_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_V = '{urn:schemas-microsoft-com:vml}'
_PKG_REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'
RASTER_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp', '.emf', '.wmf')
CAD_EXTS = ('.dxf', '.dwg')


# ════════════════════════════════════════════════════════════════════════════════════
#  1. FILE ACCESS
# ════════════════════════════════════════════════════════════════════════════════════
def _convert_to_docx(path: str) -> str:
    """Legacy .doc / .rtf / .odt -> .docx via Microsoft Word, else LibreOffice."""
    out_dir = tempfile.mkdtemp(prefix='doc2docx_')
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + '.docx')
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        try:
            d = word.Documents.Open(os.path.abspath(path), ConfirmConversions=False, ReadOnly=True,
                                    AddToRecentFiles=False)
            d.SaveAs2(os.path.abspath(out), FileFormat=16)          # wdFormatXMLDocument
            d.Close(False)
        finally:
            word.Quit()
        if os.path.isfile(out):
            logger.info('Converted %s to .docx with Microsoft Word', path)
            return out
    except Exception as ex:
        logger.warning('Word conversion failed: %s', ex)
    soffice = shutil.which('soffice') or shutil.which('soffice.exe')
    if not soffice:
        for cand in (r'C:\Program Files\LibreOffice\program\soffice.exe',
                     r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'):
            if os.path.isfile(cand):
                soffice = cand
                break
    if soffice:
        subprocess.run([soffice, '--headless', '--convert-to', 'docx', '--outdir', out_dir, path],
                       capture_output=True, timeout=180)
        if os.path.isfile(out):
            logger.info('Converted %s to .docx with LibreOffice', path)
            return out
    raise RuntimeError(f'Could not open "{os.path.basename(path)}". Save it as .docx in Word and upload again '
                       f'(Microsoft Word or LibreOffice is needed to read .doc / .rtf / .odt files).')


def _para_text(p) -> str:
    out = []
    for el in p.iter():
        if el.tag == _W + 't' and el.text:
            out.append(el.text)
        elif el.tag == _W + 'tab':
            out.append('\t')
        elif el.tag in (_W + 'br', _W + 'cr'):
            out.append('\n')
    return ''.join(out)


def _read_docx(path: str) -> Dict[str, Any]:
    """Paragraphs, tables, pictures (in reading order) and embedded CAD files of a .docx."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise RuntimeError('This file is not a valid Word document (.docx).')
    names = z.namelist()
    if 'word/document.xml' not in names:
        raise RuntimeError('This file is not a valid Word document (word/document.xml missing).')

    rels = {}
    if 'word/_rels/document.xml.rels' in names:
        for r in ET.fromstring(z.read('word/_rels/document.xml.rels')).iter(_PKG_REL + 'Relationship'):
            tgt = r.get('Target', '')
            if r.get('TargetMode') != 'External':
                tgt = os.path.normpath(os.path.join('word', tgt)).replace('\\', '/')
            rels[r.get('Id')] = tgt

    root = ET.fromstring(z.read('word/document.xml'))
    body = root.find(_W + 'body')
    paragraphs: List[str] = []
    tables: List[List[List[str]]] = []
    order: List[str] = []                      # media targets in reading order
    for el in (list(body) if body is not None else []):
        if el.tag == _W + 'p':
            t = _para_text(el).strip()
            if t:
                paragraphs.append(t)
        elif el.tag == _W + 'tbl':
            rows = []
            for tr in el.iter(_W + 'tr'):
                cells = []
                for tc in tr.findall(_W + 'tc'):
                    cells.append(' '.join(_para_text(p).strip() for p in tc.iter(_W + 'p')).strip())
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)
        for b in el.iter():
            rid = None
            if b.tag == _A + 'blip':
                rid = b.get(_R + 'embed') or b.get(_R + 'link')
            elif b.tag == _V + 'imagedata':
                rid = b.get(_R + 'id')
            if rid and rid in rels and rels[rid] not in order:
                order.append(rels[rid])

    # headers / footers often carry the project name and the drawing scale
    extra = []
    for n in names:
        if re.match(r'word/(header|footer)\d*\.xml$', n):
            try:
                extra += [_para_text(p).strip() for p in ET.fromstring(z.read(n)).iter(_W + 'p')]
            except ET.ParseError:
                pass
    media = [n for n in names if n.startswith('word/media/') or n.startswith('word/embeddings/')]
    ordered = [m for m in order if m in names] + [m for m in media if m not in order]
    pictures, cad = [], []
    for n in ordered:
        ext = os.path.splitext(n)[1].lower()
        if ext in CAD_EXTS:
            cad.append({'name': os.path.basename(n), 'data': z.read(n), 'ext': ext})
        elif ext in RASTER_EXTS:
            pictures.append({'name': os.path.basename(n), 'data': z.read(n), 'ext': ext})
        elif n.startswith('word/embeddings/'):
            data = z.read(n)
            hit = _cad_in_package(data)
            if hit:
                cad.append({'name': os.path.basename(n) + hit[1], 'data': hit[0], 'ext': hit[1]})
    return {'paragraphs': paragraphs, 'tables': tables, 'header_footer': [t for t in extra if t],
            'pictures': pictures, 'cad': cad}


def _pdf_rows_and_labels(page, dpi: float = 150.0) -> Tuple[List[str], List[Tuple[str, float, float]]]:
    """Rebuild visual text rows AND vertically-stacked room callouts of a PDF page."""
    raw_lines = []
    for b in page.get_text('dict').get('blocks', []):
        for ln in b.get('lines', []):
            sp_list = []
            for sp in ln.get('spans', []):
                t = (sp.get('text') or '').strip()
                if t:
                    x0, y0, x1, y1 = sp['bbox']
                    sp_list.append(((y0 + y1) / 2.0, x0, x1, t, max(1.0, y1 - y0)))
            ln_txt = ' '.join(s[3] for s in sp_list).strip()
            if ln_txt and 'bbox' in ln:
                lx0, ly0, lx1, ly1 = ln['bbox']
                raw_lines.append((ly0, ly1, lx0, lx1, ln_txt, sp_list))

    # First detect vertically-stacked floor-plan callouts (centered short lines: Room Name -> Dimensions)
    raw_lines.sort(key=lambda item: (item[0], item[2]))
    used_callout = [False] * len(raw_lines)
    labels: List[Tuple[str, float, float]] = []
    callout_rows: List[str] = []
    pt_to_px = float(dpi) / 72.0
    for i in range(len(raw_lines)):
        if used_callout[i]:
            continue
        ly0, ly1, lx0, lx1, ltxt, _ = raw_lines[i]
        if lx1 - lx0 > 180.0:
            continue
        is_room_head = bool(ROOM_RE.search(ltxt)) and not bool(PAIR_RE.search(ltxt))
        grp = [i]
        xc = 0.5 * (lx0 + lx1)
        cur_y1 = ly1
        if is_room_head:
            for j in range(i + 1, len(raw_lines)):
                if used_callout[j]:
                    continue
                ny0, ny1, nx0, nx1, ntxt, _ = raw_lines[j]
                if nx1 - nx0 > 180.0:
                    continue
                nxc = 0.5 * (nx0 + nx1)
                if -3.0 <= ny0 - cur_y1 <= 15.0 and abs(nxc - xc) <= 28.0:
                    if PAIR_RE.search(ntxt) and not ROOM_RE.search(ntxt):
                        grp.append(j)
                        cur_y1 = max(cur_y1, ny1)
        joined = ' '.join(raw_lines[k][4] for k in grp)
        if len(grp) >= 2 or (len(grp) == 1 and len(ltxt) <= 25 and re.search(r'^(?:DUCT|PASSAGE|3[\'’′].*PASSAGE|ENTRY|BALC\.?)$', ltxt, re.I)):
            for k in grp:
                used_callout[k] = True
            callout_rows.append(joined)
            gx = 0.5 * (min(raw_lines[k][2] for k in grp) + max(raw_lines[k][3] for k in grp)) * pt_to_px
            gy = 0.5 * (min(raw_lines[k][0] for k in grp) + max(raw_lines[k][1] for k in grp)) * pt_to_px
            labels.append((joined, round(gx, 1), round(gy, 1)))

    # Remaining lines (tables, paragraphs, notes) are grouped horizontally by baseline
    spans = [sp for idx, rl in enumerate(raw_lines) if not used_callout[idx] for sp in rl[5]]
    spans.sort()
    rows, cur = [], []
    for s in spans:
        if cur and abs(s[0] - cur[-1][0]) > 0.45 * max(s[4], cur[-1][4]):
            rows.append(cur)
            cur = []
        cur.append(s)
    if cur:
        rows.append(cur)
    out = list(callout_rows)
    for r in rows:
        r.sort(key=lambda s: s[1])
        txt = r[0][3]
        for prev, s in zip(r, r[1:]):
            txt += (' | ' if s[1] - prev[2] > 1.2 * s[4] else ' ') + s[3]
        out.append(txt)
    return out, labels


def _pdf_rows(page) -> List[str]:
    rows, _ = _pdf_rows_and_labels(page, 150.0)
    return rows


def _read_pdf(path: str) -> Dict[str, Any]:
    """PDF: text of every page, embedded plan pictures (when the page is a text specification),
    and every page rendered as a crisp picture (~150 DPI, <=2400 px)."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(path)
    paragraphs, pictures = [], []
    for pno, page in enumerate(doc):
        if pno >= 30:
            break
        long_pt = max(page.rect.width, page.rect.height)
        dpi = int(round(max(72.0, min(180.0, 2400.0 * 72.0 / max(long_pt, 1.0)))))
        page_rows, page_labels = _pdf_rows_and_labels(page, dpi=dpi)
        paragraphs += page_rows
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pictures.append({'name': f'page {pno + 1}', 'data': pix.tobytes('png'), 'ext': '.png',
                         'page_dpi': dpi, 'page_labels': page_labels})
        # If the page is a text document with an embedded figure (rather than a vector-labeled floor plan sheet),
        # also extract embedded non-mask images so the embedded figure beats the full text page in _plan_score.
        if len(page_labels) < 3:
            for k, info in enumerate(page.get_images(full=True)):
                if info[1] != 0:  # skip SMask / soft-mask streams
                    continue
                try:
                    img = doc.extract_image(info[0])
                except Exception:
                    continue
                if img and img.get('image') and min(img.get('width', 0), img.get('height', 0)) >= 250:
                    pictures.append({'name': f'page {pno + 1} picture {k + 1}', 'data': img['image'],
                                     'ext': '.' + img.get('ext', 'png')})
    return {'paragraphs': paragraphs, 'tables': [], 'header_footer': [], 'pictures': pictures, 'cad': []}


def _cad_in_package(data: bytes) -> Optional[Tuple[bytes, str]]:
    """Recover a DXF / DWG stored inside an OLE 'Package' embedding (drag-and-dropped file)."""
    i = data.find(b'AC10')
    if 0 <= i and data[i:i + 6][4:6].isdigit():
        return data[i:], '.dwg'
    m = re.search(rb'0\r?\nSECTION\r?\n\s*2\r?\nHEADER', data)
    if m:
        end = data.find(b'EOF', m.start())
        return data[m.start():(end + 3 if end > 0 else len(data))], '.dxf'
    return None


# ════════════════════════════════════════════════════════════════════════════════════
#  2. PICK THE FLOOR-PLAN PICTURE
# ════════════════════════════════════════════════════════════════════════════════════
def _picture_to_png(pic: dict, out_dir: str, idx: int) -> Optional[str]:
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(pic['data']))
        if im.format in ('WMF', 'EMF'):
            try:
                im.load(dpi=200)
            except TypeError:
                im.load()
            if max(im.size) > 6000:                       # huge vector page -> re-render smaller
                im = Image.open(io.BytesIO(pic['data']))
                im.load(dpi=max(72, int(200 * 6000 / max(im.size))))
        else:
            im.load()
        if getattr(im, 'n_frames', 1) > 1:
            im.seek(0)
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg
        im = im.convert('RGB')
        g = im.convert('L')
        if float(sum(g.getdata())) / (g.width * g.height) < 100.0:      # CAD screenshot: light lines on dark
            from PIL import ImageOps
            im = ImageOps.invert(im)
        long_side = max(im.size)
        pic['resize'] = 1.0
        if long_side < 1600:                              # small pasted picture -> upsample for wall detection
            f = 2000.0 / long_side
            im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
            pic['resize'] = f
        p = os.path.join(out_dir, f'doc_picture_{idx + 1}.png')
        im.save(p)
        return p
    except Exception as ex:
        logger.info('Picture %s skipped (%s)', pic.get('name'), ex)
        return None


def _plan_score(png: str) -> Tuple[float, str]:
    """How much the picture looks like an orthogonal floor-plan drawing (long H/V ink lines on a light page)."""
    import cv2
    import numpy as np
    g = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    if g is None:
        return 0.0, 'unreadable'
    h, w = g.shape
    if min(h, w) < 250:
        return 0.0, 'too small'
    bw = (g < 150).astype(np.uint8)
    ink = float(bw.mean())
    if ink < 0.004:
        return 0.0, 'blank'
    if ink > 0.45:
        return 0.0, 'photo / dark picture'
    k = max(25, min(h, w) // 25)
    hl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    vl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k)))
    nh, nv = int(hl.sum()), int(vl.sum())
    straight = nh + nv
    frac = straight / max(int(bw.sum()), 1)
    balance = min(nh, nv) / max(max(nh, nv), 1)            # plans have both horizontal and vertical walls
    if balance < 0.15:
        return 0.0, 'not a plan (lines in one direction only)'
    score = straight * (0.3 + frac) * (0.5 + balance)
    return float(score), f'{frac * 100:.0f}% of ink is straight H/V lines'


# ════════════════════════════════════════════════════════════════════════════════════
#  3. READ THE WRITTEN SPECIFICATION
# ════════════════════════════════════════════════════════════════════════════════════
_FT = r"(?:'|’|′|ft\.?|feet|foot)"
_IN = r'(?:"|”|″|in\.?|inch(?:es)?)'
_UNIT = (r"(mm|millimet(?:er|re)s?|cm|centimet(?:er|re)s?|met(?:er|re)s?|mtrs?\.?|m(?![a-z])|"
         r"ft\.?|feet|foot|'|’|′|inch(?:es)?|in\.?(?![a-z])|\"|”|″)")
LEN_RE = re.compile(
    r"(?<![\d.])(?:(\d+)\s*" + _FT + r"\s*[-\s]?\s*(\d+(?:\.\d+)?)\s*" + _IN + r"?"
    r"|(\d+(?:\.\d+)?)\s*" + _UNIT + r"?)", re.I)
_UNIT_NC = '(?:' + _UNIT[1:]
PAIR_RE = re.compile(
    r"(?<![\d.])((?:\d+\s*" + _FT + r"\s*[-\s]?\s*\d+(?:\.\d+)?\s*" + _IN + r"?)|(?:\d+(?:\.\d+)?\s*" + _UNIT_NC + r"?))"
    r"\s*(?:x|×|\*|by)\s*"
    r"((?:\d+\s*" + _FT + r"\s*[-\s]?\s*\d+(?:\.\d+)?\s*" + _IN + r"?)|(?:\d+(?:\.\d+)?\s*" + _UNIT_NC + r"?))", re.I)
AREA_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(sq\.?\s*m(?:t|tr|eters?|etres?)?\b|m2\b|m²|sqm\b|sq\.?\s*f(?:ee)?t\b|sft\b|ft2\b|ft²|sq\.?\s*yd)', re.I)

_UNIT_MM = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'ft': 304.8, 'in': 25.4}


def _unit_key(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    u = u.lower().strip().rstrip('.')
    if u.startswith('mm') or u.startswith('milli'):
        return 'mm'
    if u.startswith('cm') or u.startswith('centi'):
        return 'cm'
    if u in ('m', 'mtr', 'mtrs') or u.startswith('met'):
        return 'm'
    if u in ('ft', 'feet', 'foot', "'", '’', '′'):
        return 'ft'
    if u in ('in', 'inch', 'inches', '"', '”', '″'):
        return 'in'
    return None


def _parse_len(tok: str) -> Optional[Tuple[float, Optional[str]]]:
    """'3.0 m' -> (3.0, 'm'); 10'6\" -> (126.0, 'in'); '2100' -> (2100.0, None)."""
    m = LEN_RE.search(tok)
    if not m:
        return None
    if m.group(1):
        return float(m.group(1)) * 12.0 + float(m.group(2)), 'in'
    return float(m.group(3)), _unit_key(m.group(4))


def _to_mm(v: float, unit: Optional[str], kind: str, hint: Optional[str] = None) -> float:
    if unit:
        return v * _UNIT_MM[unit]
    if kind in ('height', 'door_head', 'win_h', 'room'):
        if v <= 7.0:
            return v * 1000.0
        if v <= 20.0:
            return v * (_UNIT_MM['ft'] if hint != 'm' else 1000.0)
        if v < 400.0:
            return v * 10.0
        return v
    if kind == 'sill':
        if v <= 2.0:
            return v * 1000.0
        if v <= 6.0 and hint == 'ft':
            return v * 304.8
        if v < 200.0 and v > 6.0:
            return v * 10.0 if hint != 'in' else v * 25.4
        return v
    if kind == 'thickness':
        if v <= 1.0:
            return v * 1000.0
        if v <= 18.0:
            return v * 25.4                                # "9 inch walls", "4.5 in partitions"
        if v <= 60.0:
            return v * 10.0
        return v
    return v


_RANGES = {'height': (2100.0, 6000.0), 'door_head': (1800.0, 3000.0), 'thickness': (50.0, 600.0),
           'sill': (0.0, 1800.0), 'win_h': (300.0, 3000.0), 'slab': (75.0, 450.0), 'skirt': (40.0, 250.0)}


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'\n|(?<!\d)[.;](?!\d)|\u2022', text) if s.strip()]


def _values_near(sent: str, kw: re.Match, kind: str, hint: Optional[str], window: int = 70) -> List[float]:
    """Plausible lengths (mm) near a keyword: after it first, then before it. Skips 'A x B' pairs."""
    pair_spans = [m.span() for m in PAIR_RE.finditer(sent)]
    cands = []
    for m in LEN_RE.finditer(sent):
        if any(a <= m.start() < b for a, b in pair_spans):
            continue
        if not (m.group(1) or m.group(3)):
            continue
        a, b = m.span()
        if a >= kw.end():
            dist = a - kw.end()
        elif b <= kw.start():
            dist = (kw.start() - b) + 15                   # prefer values written after the keyword
        else:
            continue
        if dist > window:
            continue
        v, u = _parse_len(m.group(0))
        mm = _to_mm(v, u, kind, hint)
        lo, hi = _RANGES.get(kind, (0, 1e9))
        if lo <= mm <= hi:
            cands.append((dist, mm))
    return [mm for _, mm in sorted(cands)]


def _pair_mm(m: re.Match, kind: str, hint: Optional[str]) -> Optional[Tuple[float, float]]:
    a, b = _parse_len(m.group(1)), _parse_len(m.group(2))
    if not a or not b:
        return None
    ua, ub = a[1] or b[1], b[1] or a[1]
    if ua is None and ub is None:
        ua = ub = _guess_pair_unit(a[0], b[0], hint)
    return _to_mm(a[0], ua, kind, hint), _to_mm(b[0], ub, kind, hint)


def _guess_pair_unit(x: float, y: float, hint: Optional[str]) -> str:
    big = max(x, y)
    if big >= 400:
        return 'mm'
    if hint in ('m', 'ft', 'mm', 'cm'):
        if hint == 'm' and big <= 25:
            return 'm'
        if hint == 'ft' and big <= 60:
            return 'ft'
        if hint == 'mm' and big >= 50:
            return 'mm'
        if hint == 'cm' and big >= 50:
            return 'cm'
    if big <= 9.0:
        return 'm'
    if big <= 45.0:
        return 'ft'
    return 'cm'


def _unit_hint(text: str) -> Optional[str]:
    t = text.lower()
    counts = {
        'ft': len(re.findall(r"\d\s*(?:'|’|′|ft\b|feet|foot)", t)),
        'm': len(re.findall(r'\d\s*(?:m\b|mtrs?\b|met(?:er|re)s?\b|sq\.?\s*m)', t)),
        'mm': len(re.findall(r'\d\s*mm\b', t)),
        'cm': len(re.findall(r'\d\s*cm\b', t)),
    }
    best = max(counts.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else None


def parse_spec(text: str) -> Tuple[Dict[str, float], List[str]]:
    """Construction values written in the document (all in mm)."""
    spec: Dict[str, float] = {}
    found: List[str] = []
    hint = _unit_hint(text)

    def put(key, val, sent):
        if key not in spec:
            spec[key] = round(float(val), 1)
            found.append(f'{key} = {val:.0f} mm  <- "{sent[:110]}"')

    rules = [
        ('wall_h', 'height', r'(floor[\s\-]*to[\s\-]*(?:ceiling|floor|slab)|clear|ceiling|wall|storey|story|room|floor)\s*'
                             r'heights?|heights?\s*of\s*(?:the\s*)?(?:walls?|ceilings?|floors?|rooms?|storey)'),
        ('ext_wall_t', 'thickness', r'(external|exterior|outer|outside|peripheral|boundary|perimeter)\s*(?:brick\s*|block\s*|masonry\s*)?walls?'),
        ('int_wall_t', 'thickness', r'(internal|interior|inner|partition|dividing)\s*(?:brick\s*|block\s*|masonry\s*)?walls?|partitions?'),
        ('wall_t', 'thickness', r'walls?\s*thickness|thickness\s*of\s*(?:all\s*)?(?:the\s*)?walls?|thick\s*(?:brick\s*|block\s*)?walls?|walls?\s*(?:are|is|shall\s*be|of)\s*[^,]{0,25}thick'),
        ('door_head', 'door_head', r'door\s*(?:clear\s*)?height|height\s*of\s*(?:the\s*)?doors?|lintel\s*(?:level|height|bottom)|door\s*head'),
        ('vent_sill', 'sill', r'(?:ventilator|vent|toilet\s*window|bath(?:room)?\s*window)s?\s*sill'),
        ('win_sill', 'sill', r'(?:window\s*)?sill\s*(?:height|level)?|sill'),
        ('win_h', 'win_h', r'window\s*(?:opening\s*)?height|height\s*of\s*(?:the\s*)?windows?'),
        ('slab_t', 'slab', r'slab\s*(?:thickness|depth)?|thickness\s*of\s*(?:the\s*)?slab'),
        ('skirt_h', 'skirt', r'skirting\s*(?:height)?'),
    ]
    for sent in _sentences(text):
        low = sent.lower()
        for key, kind, pat in rules:
            m = re.search(pat, low, re.I)
            if not m:
                continue
            if key == 'win_sill' and re.search(r'ventilator|\bvent\b|toilet|bath', low):
                key = 'vent_sill'
            if key in spec:
                continue
            if kind == 'thickness' and not re.search(r'thick|wall|partition|brick|block', low):
                continue
            vals = _values_near(sent, m, kind, hint)
            if vals:
                put(key, vals[0], sent)
        # door / window / ventilator sizes written as W x H
        for key_word, wk, hk in (('door', None, 'door_head'), ('window', None, 'win_h'), ('ventilator', None, 'vent_h'),
                                 ('vent', None, 'vent_h')):
            km = re.search(r'\b' + key_word + r's?\b', low)
            if not km:
                continue
            for pm in PAIR_RE.finditer(sent):
                if pm.start() < km.start() - 40 or pm.start() - km.end() > 80:
                    continue
                dims = _pair_mm(pm, 'door_head' if key_word == 'door' else 'win_h', hint)
                if not dims:
                    continue
                w_mm, h_mm = dims
                if key_word == 'door':
                    hh = max(w_mm, h_mm)
                    if 1800.0 <= hh <= 3000.0:
                        put(hk, hh, sent)
                        put('door_w', min(w_mm, h_mm), sent)
                else:
                    if 250.0 <= h_mm <= 2700.0:
                        put(hk, h_mm, sent)
                break
        bm = re.search(r'(\d)\s*(?:B\.?H\.?K|bed\s*room|bedroom)', sent, re.I)
        if bm and 'bhk' not in spec and re.search(r'bhk', low):
            spec['bhk'] = float(bm.group(1))
            found.append(f'bhk = {bm.group(1)}  <- "{sent[:110]}"')
        sm = re.search(r'scale\s*[:=\-]?\s*1\s*:\s*(\d{2,4})', low)
        if sm and 'scale' not in spec:
            spec['scale'] = float(sm.group(1))
            found.append(f'scale = 1:{sm.group(1)}  <- "{sent[:110]}"')
    if 'wall_t' in spec:
        spec.setdefault('ext_wall_t', spec['wall_t'])
        spec.setdefault('int_wall_t', spec['wall_t'])
    return spec, found


# ════════════════════════════════════════════════════════════════════════════════════
#  4. ROOM SCHEDULE
# ════════════════════════════════════════════════════════════════════════════════════
ROOM_RE = re.compile(
    r'(?<![A-Za-z])((?:master|guest|kids?|children|parents?|common|attached|family|main|second|third|1st|2nd|3rd|4th|'
    r'm\.|c\.|ent\.)?\s*'
    r'(?:bed\s*room|bedroom|bed\b|toilet|bath\s*room|bathroom|bath\b|w\.?\s*c\b|wash\s*room|washroom|powder\s*room|'
    r'kitchen|pantry|living(?:\s*(?:room|area|hall))?(?:\s*(?:&|and|/|cum|\+|\-)\s*din(?:ing)?)?|drawing\s*room|lounge|hall|'
    r'dining(?:\s*(?:room|area))?|dry\s*balc(?:ony)?\.?|balc(?:ony)?\.?|sit[\s\-]*out|terrace|deck|verandah|veranda|porch|utility|'
    r'store(?:\s*room)?|pooja(?:\s*room)?|puja(?:\s*room)?|prayer\s*room|study(?:\s*room)?|office|library|'
    r'foyer|lobby|entrance|passage|corridor|walk[\s\-]*in(?:\s*wardrobe|\s*closet)?|wardrobe|dress(?:ing)?(?:\s*room)?|'
    r'servant(?:\s*room)?|maid(?:\'?s)?\s*room|laundry|wash\s*area|staircase|stair|lift|duct|shaft)'
    r'(?:\s*(?:no\.?\s*)?[-#]?\s*(?:\d{1,2}|[ivx]{1,3}|[a-d])\b'
    r'(?![\d.\'’′"”″]|\s*(?:x|×|by|\*|mm|cm|m\b|mtr|met|ft|feet|foot|in\b|inch|sq|\')))?)', re.I)
_SPEC_WORDS = re.compile(r'ventilator|window|door|sill|lintel|thick|height|slab|skirting|plaster|finish', re.I)


def _normalize_room_name(raw: str) -> str:
    s = re.sub(r'\s+', ' ', raw).strip(' -:#.').title()
    s = re.sub(r'^M\.?\s*Bed(?:room)?\b', 'Master Bedroom', s, flags=re.I)
    s = re.sub(r'^M\.?\s*Toilet\b', 'Master Toilet', s, flags=re.I)
    s = re.sub(r'^C\.?\s*Toilet\b', 'Common Toilet', s, flags=re.I)
    s = re.sub(r'^Ent\.?\s*Lobby\b', 'Entrance Lobby', s, flags=re.I)
    s = re.sub(r'^Living[\s\-]+Din(?:ing)?\b', 'Living & Dining', s, flags=re.I)
    s = re.sub(r'^Balc\.?$', 'Balcony', s, flags=re.I)
    s = re.sub(r'^Dry\s+Balc\.?$', 'Dry Balcony', s, flags=re.I)
    return s


def _room_entries_from_line(line: str, hint: Optional[str], header_unit: Optional[str] = None,
                            first_only: bool = False) -> List[dict]:
    out = []
    names = list(ROOM_RE.finditer(line))
    if first_only:
        names = names[:1]
    for k, nm in enumerate(names):
        seg_end = names[k + 1].start() if k + 1 < len(names) else len(line)
        seg = line[nm.end():seg_end]
        if re.match(r'\s*(?:doors?|windows?|ventilators?|sills?|walls?|lights?|fans?)\b', seg, re.I):
            continue                                   # "main entrance door 1000 x 2100" is not a room
        name = _normalize_room_name(nm.group(1))
        entry = {'name': name, 'source': line.strip()[:140]}
        pm = PAIR_RE.search(seg)
        if pm:
            a, b = _parse_len(pm.group(1)), _parse_len(pm.group(2))
            if a and b:
                ua, ub = a[1] or b[1] or header_unit, b[1] or a[1] or header_unit
                if ua is None:
                    ua = ub = _guess_pair_unit(a[0], b[0], hint)
                w, l = a[0] * _UNIT_MM[ua], b[0] * _UNIT_MM[ub]
                if 600.0 <= min(w, l) and max(w, l) <= 25000.0:
                    entry['w_mm'], entry['l_mm'] = round(min(w, l)), round(max(w, l))
        if 'w_mm' not in entry:
            am = AREA_RE.search(seg)
            if am:
                v, u = float(am.group(1)), am.group(2).lower()
                m2 = v if ('m' in u and 'f' not in u and 'yd' not in u) else (v * 0.836127 if 'yd' in u else v * 0.092903)
                if 0.5 <= m2 <= 400.0:
                    entry['area_m2'] = round(m2, 2)
        if 'w_mm' not in entry and 'area_m2' not in entry and header_unit:
            nums = [float(x) for x in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])', seg)][:2]
            if len(nums) == 2:
                w, l = nums[0] * _UNIT_MM[header_unit], nums[1] * _UNIT_MM[header_unit]
                if 600.0 <= min(w, l) and max(w, l) <= 25000.0:
                    entry['w_mm'], entry['l_mm'] = round(min(w, l)), round(max(w, l))
        out.append(entry)
    return out


def parse_schedule(paragraphs: List[str], tables: List[List[List[str]]], hint: Optional[str]) -> List[dict]:
    entries: List[dict] = []
    flat_lines: List[str] = []
    for p in paragraphs:
        for line in p.split('\n'):
            if line.strip():
                flat_lines.append(line.strip())
                entries += _room_entries_from_line(line, hint, first_only=' | ' in line)
    for i in range(len(flat_lines) - 1):
        if ROOM_RE.search(flat_lines[i]) and not PAIR_RE.search(flat_lines[i]) and PAIR_RE.search(flat_lines[i + 1]):
            if not ROOM_RE.search(flat_lines[i + 1]):
                entries += _room_entries_from_line(flat_lines[i] + ' ' + flat_lines[i + 1], hint, first_only=True)
    for rows in tables:
        header_unit = None
        head = ' '.join(rows[0]).lower() if rows else ''
        if re.search(r'length|width|breadth|size|dimension|area', head):
            hm = re.search(r'\(\s*(mm|cm|m|ft|feet|in)\s*\)|\b(mm|cm|ft|feet|meters?|metres?)\b', head)
            header_unit = _unit_key(hm.group(1) or hm.group(2)) if hm else None
        for r in rows:
            entries += _room_entries_from_line(' | '.join(r), hint, header_unit, first_only=True)
    # keep one entry per room (prefer one with a size)
    best: Dict[str, dict] = {}
    for e in entries:
        key = e['name'].lower()
        cur = best.get(key)
        rank = 2 if 'w_mm' in e else (1 if 'area_m2' in e else 0)
        if cur is None or rank > (2 if 'w_mm' in cur else (1 if 'area_m2' in cur else 0)):
            best[key] = e
    # drop generic words that are only part of sentences ("toilet ventilators 600 x 450") with no size
    out = [e for e in best.values() if 'w_mm' in e or 'area_m2' in e
           or (len(e['name']) > 3 and not _SPEC_WORDS.search(e['source']))]
    return out


def footprint_px(png: str) -> float:
    """Pixel area of the building footprint drawn in a plan picture (outline filled, door gaps sealed)."""
    import cv2
    import numpy as np
    from .line_vectorizer import _strip_sheet_borders
    g = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    if g is None:
        return 0.0
    bw0 = (g < 150).astype(np.uint8)
    _strip_sheet_borders(bw0)
    bw = cv2.copyMakeBorder(bw0 * 255, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=0)
    k = max(5, int(max(g.shape) * 0.015))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    ff = closed.copy()
    cv2.floodFill(ff, np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8), (0, 0), 255)
    filled = closed | cv2.bitwise_not(ff)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((filled > 0).astype(np.uint8), connectivity=8)
    if n <= 1:
        return 0.0
    areas = [float(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] < 0.88 * g.shape[0] * g.shape[1]]
    return max(areas) if areas else float(stats[1:, cv2.CC_STAT_AREA].max())


def schedule_area_m2(schedule: List[dict]) -> Tuple[float, int]:
    tot, n = 0.0, 0
    for e in schedule:
        if 'w_mm' in e:
            tot += e['w_mm'] * e['l_mm'] / 1e6
            n += 1
        elif 'area_m2' in e:
            tot += e['area_m2']
            n += 1
    return tot, n


# carpet (room) area / footprint area incl. walls and small circulation for a typical flat plan
CARPET_TO_FOOTPRINT = 0.86


# ════════════════════════════════════════════════════════════════════════════════════
#  5. ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════════
_CACHE: Dict[Tuple[str, float, int], Dict[str, Any]] = {}


def read_document(path: str) -> Dict[str, Any]:
    """Read a Word document (cached per file version) -> plan path, specification, room schedule."""
    import copy
    key = (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path))
    if key in _CACHE and os.path.isfile(_CACHE[key]['plan_path']):
        return copy.deepcopy(_CACHE[key])
    d = _read_document(path)
    _CACHE[key] = copy.deepcopy(d)
    return d


def _read_document(path: str) -> Dict[str, Any]:
    """Read a Word document -> {'plan_path', 'plan_kind', 'spec', 'schedule', 'notes', ...}."""
    src = path
    low = path.lower()
    if low.endswith('.pdf'):
        d = _read_pdf(path)
    else:
        if not low.endswith(('.docx', '.docm', '.dotx', '.dotm')):
            src = _convert_to_docx(path)
        d = _read_docx(src)
    text = '\n'.join(d['paragraphs'] + d['header_footer'] +
                     [' | '.join(r) for t in d['tables'] for r in t])
    hint = _unit_hint(text)
    spec, found = parse_spec(text)
    schedule = parse_schedule(d['paragraphs'], d['tables'], hint)
    notes: List[str] = []

    work = tempfile.mkdtemp(prefix='docplan_')
    plan_path, plan_kind, plan_name, plan_reason = '', '', '', ''
    if d['cad']:
        c = max(d['cad'], key=lambda c: len(c['data']))
        plan_path = os.path.join(work, 'document_plan' + c['ext'])
        with open(plan_path, 'wb') as fh:
            fh.write(c['data'])
        plan_kind, plan_name, plan_reason = 'cad', c['name'], f'embedded {c["ext"].upper()[1:]} drawing'
    pics = []
    for i, pic in enumerate(d['pictures']):
        png = _picture_to_png(pic, work, i)
        if not png:
            continue
        score, why = _plan_score(png)
        rsz = float(pic.get('resize', 1.0))
        dpi = pic.get('page_dpi') and pic['page_dpi'] * rsz
        lbls = [(t, x * rsz, y * rsz) for t, x, y in (pic.get('page_labels') or [])]
        pics.append({'name': pic['name'], 'png': png, 'score': score, 'why': why, 'dpi': dpi or None, 'labels': lbls})
    plan_dpi = None
    plan_labels: List[Tuple[str, float, float]] = []
    if not plan_path:
        good = [p for p in pics if p['score'] > 0]
        if good:
            best = max(good, key=lambda p: p['score'])
            plan_path, plan_kind, plan_name, plan_reason = best['png'], 'image', best['name'], best['why']
            plan_dpi = best['dpi']
            plan_labels = best.get('labels') or []
            for p in pics:
                if p is not best:
                    notes.append(f'picture {p["name"]} not used as the plan ({p["why"] if p["score"] <= 0 else "weaker plan match"})')
    if not plan_path:
        what = []
        if spec:
            what.append(f'{len(spec)} specification value(s)')
        if schedule:
            what.append(f'{len(schedule)} room(s) in the schedule')
        pic_info = '; '.join(f'{p["name"]}: {p["why"]}' for p in pics) or 'no pictures'
        raise RuntimeError(
            'The document has no floor-plan drawing to build walls from '
            f'({pic_info}). It was read ({", ".join(what) or "no plan data found"}), but a plan is needed: '
            'insert the floor plan as a picture (PNG / JPG / EMF) or attach the DXF / DWG in the document.')

    logger.info('Document: plan from %s (%s); %d spec values; %d schedule rooms',
                plan_name, plan_reason, len(spec), len(schedule))
    fp_px = footprint_px(plan_path) if plan_kind == 'image' else 0.0
    sched_area, n_sized = schedule_area_m2(schedule)
    return {
        'file': os.path.basename(path), 'plan_path': plan_path, 'plan_kind': plan_kind,
        'plan_source': plan_name, 'plan_reason': plan_reason, 'plan_dpi': plan_dpi,
        'plan_labels': plan_labels,
        'footprint_px': fp_px, 'schedule_area_m2': round(sched_area, 2), 'schedule_sized': n_sized,
        'spec': spec, 'spec_found': found, 'schedule': schedule, 'unit_hint': hint,
        'paragraph_count': len(d['paragraphs']), 'table_count': len(d['tables']),
        'picture_count': len(d['pictures']), 'cad_count': len(d['cad']),
        'text_excerpt': text[:1500], 'notes': notes,
    }


# ════════════════════════════════════════════════════════════════════════════════════
#  6. MATCH THE SCHEDULE TO THE DETECTED ROOMS (used by architecture.analyse)
# ════════════════════════════════════════════════════════════════════════════════════
def _entry_cost(rm: dict, e: dict, s: float) -> float:
    area = rm['area_m2'] * s * s
    if 'w_mm' in e:
        rmin, rmax = max(rm['min_dim'] * s, 1.0), max(rm['max_dim'] * s, 1.0)
        c = abs(math.log(rmin / e['w_mm'])) + abs(math.log(rmax / e['l_mm']))
        c += 0.5 * abs(math.log(max(area, 1e-3) / (e['w_mm'] * e['l_mm'] / 1e6)))
        return c
    return 1.5 * abs(math.log(max(area, 1e-3) / e['area_m2']))


def match_schedule(rooms: List[dict], schedule: List[dict], allow_scale: bool) -> Dict[str, Any]:
    """Assign schedule entries to rooms by size (and find the drawing scale for raster plans).
    Returns {'scale', 'pairs': [(room_idx, entry, cost)], 'unmatched': [entry]}."""
    sized = [e for e in schedule if 'w_mm' in e or 'area_m2' in e]
    if not sized or not rooms:
        return {'scale': 1.0, 'pairs': [], 'unmatched': list(schedule)}
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    CAP, ACCEPT = 0.8, 0.40

    def solve(s):
        C = np.array([[min(_entry_cost(rm, e, s), CAP) for rm in rooms] for e in sized])
        ri, ci = linear_sum_assignment(C)
        tot = float(C[ri, ci].sum()) + CAP * (len(sized) - len(ri))
        return tot, [(int(c), sized[r], float(C[r, c])) for r, c in zip(ri, ci)]

    scales = [1.0]
    if allow_scale:
        scales = [math.exp(math.log(0.5) + i * (math.log(2.0) - math.log(0.5)) / 280.0) for i in range(281)]
    best = min((solve(s) + (s,) for s in scales), key=lambda t: t[0])
    tot, pairs, s = best
    good = [p for p in pairs if p[2] <= ACCEPT]
    if allow_scale and len([p for p in good if 'w_mm' in p[1]]) < 2:
        tot, pairs = solve(1.0)
        s = 1.0
        good = [p for p in pairs if p[2] <= ACCEPT]
    used = {id(p[1]) for p in good}
    return {'scale': s, 'pairs': good, 'unmatched': [e for e in schedule if id(e) not in used]}
