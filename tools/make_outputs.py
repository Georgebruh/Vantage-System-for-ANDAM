#!/usr/bin/env python3
"""Regenerate the drawing outputs from the KiCad files with kicad-cli (KiCad 7 to 10).

    pip install pypdf reportlab
    python3 tools/make_outputs.py            # both boards
    python3 tools/make_outputs.py power      # one board: sensor or power

Writes, for each board (<B> is Sensor or Power, <b> is sensor or power)
  outputs/<b>-board/Vantage_<B>_Schematic.pdf
  outputs/<b>-board/Vantage_<B>_Copper-Artwork_Letter.pdf   (1:1, four copies, portrait)
  outputs/<b>-board/Vantage_<B>_Copper-Artwork_A4.pdf       (1:1, four copies, portrait)
  outputs/<b>-board/Vantage_<B>_Assembly-Drawing.pdf        (2:1, component side + copper side)
  docs/src/figures/<b>_*.svg                                (figures used by the documents)
and for the power board
  outputs/power-board/Vantage_Power_Envelope.pdf            (1:1, space the module needs in the enclosure)
  docs/src/figures/power_envelope.svg
The BOM and drill CSV files are kept by hand.
"""
import io
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "src" / "figures"
CLI = os.environ.get("KICAD_CLI", "kicad-cli")
MMPT = 72 / 25.4
BOARDS = {
    "sensor": {"dir": ROOT / "sensor-board", "stem": "Vantage_Sensor", "out": ROOT / "outputs" / "sensor-board",
               "title": "Sensor board"},
    "power": {"dir": ROOT / "power-board", "stem": "Vantage_Power", "out": ROOT / "outputs" / "power-board",
              "title": "Power board"},
}


def run(*cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stdout}{r.stderr}")


def board_box(pcb_text):
    """board outline (x0, y0, x1, y1) in page mm, from the Edge.Cuts items"""
    xs, ys = [], []
    starts = [m.start() for m in re.finditer(r"\((?:gr_line|gr_rect)\b", pcb_text)]
    for i, s in enumerate(starts):
        item = pcb_text[s:starts[i + 1] if i + 1 < len(starts) else s + 800]
        if '(layer "Edge.Cuts")' not in item:
            continue
        m = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)", item)
        xs += [float(m.group(1)), float(m.group(3))]
        ys += [float(m.group(2)), float(m.group(4))]
    return min(xs), min(ys), max(xs), max(ys)


def board_copy(b, tmp, paper, portrait=True, hide_values=False):
    """copy of the board with another paper size, same file name (the title block shows it)"""
    text = (b["dir"] / f"{b['stem']}.kicad_pcb").read_text(encoding="utf-8")
    text = re.sub(r'\(paper "[^"]*"( portrait)?\)', f'(paper "{paper}"{" portrait" if portrait else ""})', text, count=1)
    if hide_values:      # move value texts off the fabrication layers so only references show
        text = re.sub(r'(\((?:fp_text value|property "Value") "[^"]*"\s*(?:\(at [^)]*\)\s*)?(?:\(unlocked [^)]*\)\s*)?)\(layer "([FB])\.Fab"\)',
                      r'\1(layer "User.9")', text)
    d = Path(tmp) / f"{b['stem']}_{paper}{'p' if portrait else 'l'}{'v' if hide_values else ''}"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{b['stem']}.kicad_pcb"
    p.write_text(text, encoding="utf-8")
    return p, text


def pdf(pcb, out, layers, frame=False, mirror=False, drill="0"):
    cmd = [CLI, "pcb", "export", "pdf", "--layers", layers, "--black-and-white", "--drill-shape-opt", drill, "-o", out]
    if frame:
        cmd.append("--ibt")
    if mirror:
        cmd.append("--mirror")
    run(*cmd, pcb)
    return PdfReader(str(out)).pages[0]


def artwork(b, tmp, paper, out):
    pcb, text = board_copy(b, tmp, paper)
    x0, y0, x1, y1 = board_box(text)
    page = pdf(pcb, Path(tmp) / "aw_framed.pdf", "B.Cu,Edge.Cuts,Dwgs.User", frame=True, drill="1")
    bare = pdf(pcb, Path(tmp) / "aw_bare.pdf", "B.Cu,Edge.Cuts,Dwgs.User", drill="1")
    pitch = (y1 - y0) + 15.0                            # board + scale line + gap
    for k in (1, 2, 3):
        page.merge_transformed_page(bare, Transformation().translate(0, -k * pitch * MMPT))
    w = PdfWriter()
    w.add_page(page)
    w.add_metadata({"/Title": f"Vantage, {b['title']}, copper artwork (B.Cu) 1:1", "/Author": "Team sevenUP"})
    with open(out, "wb") as f:
        w.write(f)


def label(text, size_mm, y_mm):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(size_mm[0] * MMPT, size_mm[1] * MMPT))
    c.setFont("Helvetica", 9)
    c.drawCentredString(size_mm[0] / 2 * MMPT, (size_mm[1] - y_mm) * MMPT, text)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def assembly_drawing(b, tmp, out, scale=2.0):
    pcb, text = board_copy(b, tmp, "A4", portrait=False)
    x0, y0, x1, y1 = board_box(text)
    W, H = 297.0, 210.0
    frame = Path(tmp) / "frame.pdf"
    w = PdfWriter()
    views = (("F.Cu,F.Fab,F.SilkS,Edge.Cuts", False, "VIEW FROM COMPONENT SIDE, SCALE 2:1"),
             ("B.Mask,B.Fab,Edge.Cuts", True, "VIEW FROM COPPER SIDE (SMD PARTS AND PADS), SCALE 2:1"))
    for i, (layers, mirror, text_label) in enumerate(views):
        page = pdf(pcb, frame, "User.9", frame=True)
        board = pdf(pcb, Path(tmp) / f"view{i}.pdf", layers, mirror=mirror)
        cx = (x0 + x1) / 2
        cx = W - cx if mirror else cx
        cy = (y0 + y1) / 2
        tx, ty = W / 2, 95.0                            # where the board centre goes (mm from top-left)
        t = (Transformation().translate(-cx * MMPT, -(H - cy) * MMPT).scale(scale, scale)
             .translate(tx * MMPT, (H - ty) * MMPT))
        page.merge_transformed_page(board, t)
        page.merge_page(label(text_label, (W, H), ty + (y1 - y0) * scale / 2 + 16))
        w.add_page(page)
    w.add_metadata({"/Title": f"Vantage, {b['title']}, assembly drawing", "/Author": "Team sevenUP"})
    with open(out, "wb") as f:
        w.write(f)


def figures(b, key, tmp):
    FIG.mkdir(parents=True, exist_ok=True)
    pcb, _ = board_copy(b, tmp, "A4", hide_values=True)
    views = {f"{key}_component_side": ("F.Cu,F.Fab,F.SilkS,Edge.Cuts", []),
             f"{key}_copper_side": ("B.Mask,B.Fab,Edge.Cuts", ["--mirror"]),
             f"{key}_copper_artwork": ("B.Cu,Edge.Cuts", [])}
    for name, (layers, extra) in views.items():
        out = FIG / f"{name}.svg"
        run(CLI, "pcb", "export", "svg", "--layers", layers, *extra, "--black-and-white", "--page-size-mode", "2",
            "--exclude-drawing-sheet", "-o", out, pcb)
        svg = out.read_text(encoding="utf-8")       # drop the export time stamp so unchanged figures give no diff
        out.write_text(re.sub(r"<title>.*?</title>", f"<title>{name}</title>", svg, count=1), encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------
# Module envelope of the power board: the space the assembled board needs in the enclosure.
# Zones are the component side courtyards of the Rev B layout (board coordinates, mm) with the height that the
# fitted part reaches above the board. Heights are for the parts listed in VNT-002; measure the modules you buy.

BOARD_T = 1.6          # laminate
BOTTOM_H = 3.0         # copper side: SMD parts, solder joints, clipped leads
PLUG = 12.0            # free length beyond a board end for a mated JST XH plug and the bend of its cable
ENVELOPE = [           # ref, shape, geometry, height above the board, label
    ("BT1", "rect", (49.61, 50.05, 62.11, 58.45), 7.0, "BT1 battery"),
    ("J2", "rect", (49.60, 68.75, 58.20, 76.75), 11.0, "J2 solar"),
    ("U1", "rect", (63.45, 49.40, 68.55, 76.40), 39.0, "U1"),
    ("U2", "rect", (74.45, 49.40, 79.55, 76.40), 39.0, "U2"),
    ("M1", "rect", (83.05, 50.00, 127.60, 78.00), 20.0, "M1 CN3791 module"),
    ("L1", "circle", (133.10, 55.60, 4.25), 12.0, "L1"),
    ("C9", "circle", (144.60, 65.80, 3.40), 13.0, "C9"),
    ("J1", "rect", (148.00, 58.05, 160.50, 76.45), 7.0, "J1 sensor"),
]


class Drawing:
    """minimal vector drawing in page mm (origin top left, y down), written as SVG or PDF"""

    def __init__(self, w, h):
        self.w, self.h, self.items = w, h, []

    def line(self, x1, y1, x2, y2, lw=0.25, dash=None):
        self.items.append(("line", (x1, y1, x2, y2), lw, dash))

    def rect(self, x0, y0, x1, y1, lw=0.25, dash=None, fill=None):
        self.items.append(("rect", (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)), lw, dash, fill))

    def circle(self, x, y, r, lw=0.25, dash=None, fill=None):
        self.items.append(("circle", (x, y, r), lw, dash, fill))

    def text(self, x, y, s, size=2.5, anchor="start", angle=0, bold=False):
        self.items.append(("text", (x, y), s, size, anchor, angle, bold))

    def arrow(self, x1, y1, x2, y2, lw=0.25):
        self.line(x1, y1, x2, y2, lw)
        a = math.atan2(y2 - y1, x2 - x1)
        for s in (-1, 1):
            self.line(x2, y2, x2 - 2.0 * math.cos(a + s * 0.3), y2 - 2.0 * math.sin(a + s * 0.3), lw)

    def dim_h(self, xa, xb, yfeat_a, yfeat_b, yline, txt):
        """horizontal dimension from xa to xb, drawn at yline, extension lines from the features"""
        for x, yf in ((xa, yfeat_a), (xb, yfeat_b)):
            self.line(x, yf + (0.8 if yline > yf else -0.8), x, yline + (1.2 if yline > yf else -1.2), 0.18)
        m = (xa + xb) / 2
        self.arrow(m, yline, xa, yline, 0.18)
        self.arrow(m, yline, xb, yline, 0.18)
        self.text(m, yline - 0.9, txt, 2.5, "middle")

    def dim_v(self, ya, yb, xfeat_a, xfeat_b, xline, txt):
        """vertical dimension from ya to yb, drawn at xline, text on the left of the line"""
        for y, xf in ((ya, xfeat_a), (yb, xfeat_b)):
            self.line(xf + (0.8 if xline > xf else -0.8), y, xline + (1.2 if xline > xf else -1.2), y, 0.18)
        m = (ya + yb) / 2
        self.arrow(xline, m, xline, ya, 0.18)
        self.arrow(xline, m, xline, yb, 0.18)
        self.text(xline - 0.9, m, txt, 2.5, "middle", 90)

    def svg(self, title):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" '
               f'viewBox="0 0 {self.w} {self.h}"><title>{title}</title>',
               f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="white"/>',
               '<g fill="none" stroke="black" stroke-linecap="round" font-family="Helvetica, Arial, sans-serif">']
        for it in self.items:
            kind = it[0]
            if kind == "text":
                (x, y), s, size, anchor, angle, bold = it[1:]
                rot = f' transform="rotate({-angle:.2f} {x:.2f} {y:.2f})"' if angle else ""
                wt = ' font-weight="bold"' if bold else ""
                s = s.replace("&", "&amp;").replace("<", "&lt;")
                out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" fill="black" '
                           f'stroke="none"{wt}{rot}>{s}</text>')
                continue
            lw, dash = it[2], it[3]
            st = f' stroke-width="{lw}"' + (f' stroke-dasharray="{dash[0]} {dash[1]}"' if dash else "")
            if kind == "line":
                x1, y1, x2, y2 = it[1]
                out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"{st}/>')
            elif kind == "rect":
                x, y, w, h = it[1]
                f = f' fill="{it[4]}"' if it[4] else ""
                out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"{st}{f}/>')
            else:
                x, y, r = it[1]
                f = f' fill="{it[4]}"' if it[4] else ""
                out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"{st}{f}/>')
        out.append("</g></svg>")
        return "\n".join(out) + "\n"

    def pdf(self, out, title):
        c = canvas.Canvas(str(out), pagesize=(self.w * MMPT, self.h * MMPT))
        c.setTitle(title)
        c.setAuthor("Team sevenUP")
        Y = lambda y: (self.h - y) * MMPT     # noqa: E731
        for it in self.items:
            kind = it[0]
            if kind == "text":
                (x, y), s, size, anchor, angle, bold = it[1:]
                c.saveState()
                c.translate(x * MMPT, Y(y))
                c.rotate(angle)
                c.setFont("Helvetica-Bold" if bold else "Helvetica", size * MMPT)
                {"start": c.drawString, "middle": c.drawCentredString, "end": c.drawRightString}[anchor](0, 0, s)
                c.restoreState()
                continue
            lw, dash = it[2], it[3]
            c.setLineWidth(lw * MMPT)
            c.setLineCap(1)
            c.setDash([dash[0] * MMPT, dash[1] * MMPT] if dash else [])
            if kind == "line":
                x1, y1, x2, y2 = it[1]
                c.line(x1 * MMPT, Y(y1), x2 * MMPT, Y(y2))
            elif kind == "rect":
                x, y, w, h = it[1]
                if it[4]:
                    c.setFillColor(Color(0.85, 0.85, 0.85))
                c.rect(x * MMPT, Y(y + h), w * MMPT, h * MMPT, stroke=1, fill=1 if it[4] else 0)
            else:
                x, y, r = it[1]
                if it[4]:
                    c.setFillColor(Color(0.85, 0.85, 0.85))
                c.circle(x * MMPT, Y(y), r * MMPT, stroke=1, fill=1 if it[4] else 0)
        c.showPage()
        c.save()


def holes(pcb_text):
    out = []
    for chunk in pcb_text.split("\n  (footprint ")[1:]:
        if "MountingHole" not in chunk.split("\n", 1)[0]:
            continue
        m = re.search(r"\n    \(at ([-\d.]+) ([-\d.]+)", chunk)
        out.append((float(m.group(1)), float(m.group(2))))
    return sorted(out)


def envelope_views(d, text, a, bz, c):
    """the three views at 1:1: a = page position of the board corner in view A, bz = page y of the board top in
    view B, c = page position of the centre of view C"""
    x0, y0, x1, y1 = board_box(text)
    L, Wd = x1 - x0, y1 - y0
    top = max(z[3] for z in ENVELOPE)
    zmin, zmax = -BOTTOM_H, BOARD_T + top
    dia = math.ceil(math.hypot(Wd, zmax - zmin))
    # ---- view A: component side
    ox, oy = a[0] - x0, a[1] - y0
    P = lambda x, y: (x + ox, y + oy)                 # noqa: E731
    d.text(a[0], a[1] - 9, "A  COMPONENT SIDE", 3.0, bold=True)
    d.rect(*P(x0, y0), *P(x1, y1), 0.5)
    for ref, shape, g, h, lab in ENVELOPE:
        if shape == "rect":
            d.rect(*P(g[0], g[1]), *P(g[2], g[3]), 0.25, (1.2, 0.8))
        else:
            d.circle(*P(g[0], g[1]), g[2], 0.25, (1.2, 0.8))
    for hx, hy in holes(text):
        d.circle(*P(hx, hy), 1.6, 0.3)
        d.line(*P(hx - 2.6, hy), *P(hx + 2.6, hy), 0.13)
        d.line(*P(hx, hy - 2.6), *P(hx, hy + 2.6), 0.13)
    (ha, hb) = holes(text)
    bx0, by0 = P(x0, y0)
    bx1, by1 = P(x1, y1)
    hax, hay = P(*ha)
    hbx, hby = P(*hb)
    d.dim_h(bx0, bx1, by1, by1, by1 + 16, f"{L:.1f}")
    d.dim_h(bx0, hax, by1, hay, by1 + 6, f"{ha[0] - x0:.1f}")
    d.dim_h(bx0, hbx, by1, hby, by1 + 11, f"{hb[0] - x0:.1f}")
    d.dim_v(by0, by1, bx0, bx0, bx0 - 16, f"{Wd:.1f}")
    d.dim_v(hay, by1, hax, bx0, bx0 - 6, f"{y1 - ha[1]:.1f}")
    d.dim_v(hby, by1, hbx, bx1, bx1 + 8, f"{y1 - hb[1]:.1f}")
    d.text(hax - 2.4, hay - 2.2, "2 × M3", 2.2, "end")
    for ref, shape, g, h, lab in ENVELOPE:
        if ref in ("U1", "U2"):
            continue
        cx, cy = (P((g[0] + g[2]) / 2, (g[1] + g[3]) / 2) if shape == "rect" else P(g[0], g[1]))
        d.text(cx, cy + 0.9, f"{ref} {h:.0f}", 2.2, "middle")
    d.text(*P(71.5, 47.6), "U1, U2 39", 2.2, "middle")
    d.arrow(bx0 - 19, P(0, 54.2)[1], bx0 - 30, P(0, 54.2)[1])
    d.text(bx0 - 20, P(0, 53.2)[1], "battery", 2.2, "end")
    d.arrow(bx0 - 19, P(0, 72.7)[1], bx0 - 30, P(0, 72.7)[1])
    d.text(bx0 - 20, P(0, 71.7)[1], "panel", 2.2, "end")
    d.arrow(bx1 + 13, P(0, 67.3)[1], bx1 + 22, P(0, 67.3)[1])
    d.text(bx1 + 14, P(0, 66.3)[1], "sensor", 2.2)
    # ---- view B: side view, the long edge without H2 toward the viewer
    Z = lambda z: bz - (z - BOARD_T)                   # noqa: E731
    d.text(a[0], Z(top + BOARD_T) - 6, "B  SIDE VIEW", 3.0, bold=True)
    d.rect(ox + x0, Z(BOARD_T), ox + x1, Z(0), 0.5, fill="#d9d9d9")
    d.rect(ox + x0, Z(0), ox + x1, Z(zmin), 0.25, (1.2, 0.8))
    for ref, shape, g, h, lab in ENVELOPE:
        xa, xb = (g[0], g[2]) if shape == "rect" else (g[0] - g[2], g[0] + g[2])
        d.rect(ox + xa, Z(BOARD_T), ox + xb, Z(BOARD_T + h), 0.25, (1.2, 0.8))
    d.rect(ox + x0 - PLUG, Z(BOARD_T), ox + x0, Z(BOARD_T + 11), 0.18, (0.6, 0.8))
    d.rect(ox + x1, Z(BOARD_T), ox + x1 + PLUG, Z(BOARD_T + 7), 0.18, (0.6, 0.8))
    d.dim_v(Z(zmax), Z(zmin), ox + x1 + PLUG, ox + x1 + PLUG, ox + x1 + PLUG + 10, f"{zmax - zmin:.1f}")
    d.dim_h(ox + x0 - PLUG, ox + x1 + PLUG, Z(zmin), Z(zmin), Z(zmin) + 8, f"{L + 2 * PLUG:.0f}")
    d.dim_h(ox + x0 - PLUG, ox + x0, Z(BOARD_T + 11), Z(BOARD_T + 11), Z(BOARD_T + 11) - 4, f"{PLUG:.0f}")
    d.dim_h(ox + x1, ox + x1 + PLUG, Z(BOARD_T + 7), Z(BOARD_T + 7), Z(BOARD_T + 11) - 4, f"{PLUG:.0f}")
    d.dim_v(Z(zmax), Z(BOARD_T), ox + 63.45, ox + x0, ox + x0 - 18, f"{top:.0f}")
    d.dim_v(Z(BOARD_T), Z(0), ox + x0, ox + x0, ox + x0 - 18, "")
    d.text(ox + x0 - 19.5, Z(0.8) + 0.9, f"{BOARD_T}", 2.2, "end")
    d.dim_v(Z(0), Z(zmin), ox + x0, ox + x0, ox + x0 - 18, "")
    d.text(ox + x0 - 19.5, Z(zmin / 2) + 0.9, f"{BOTTOM_H:.0f}", 2.2, "end")
    d.text(ox + 71.5, Z(top + BOARD_T) - 1.5, "U1, U2", 2.2, "middle")
    d.text(ox + 105.3, Z(BOARD_T + 20) - 1.5, "M1", 2.2, "middle")
    d.text(ox + x1 + PLUG / 2, Z(BOARD_T + 7) - 1.5, "plug", 2.2, "middle")
    d.text(ox + x0 - PLUG / 2, Z(BOARD_T + 11) - 1.5, "plugs", 2.2, "middle")
    # ---- view C: end view and the smallest round tube
    cx0, cz = c
    zc = (zmin + zmax) / 2
    E = lambda yy, z: (cx0 + yy, cz - (z - zc))        # noqa: E731
    d.text(cx0 - dia / 2, cz - dia / 2 - 6, "C  END VIEW, SMALLEST ROUND TUBE", 3.0, bold=True)
    d.rect(*E(-Wd / 2, BOARD_T), *E(Wd / 2, 0), 0.5, fill="#d9d9d9")
    d.rect(*E(-Wd / 2, 0), *E(Wd / 2, zmin), 0.25, (1.2, 0.8))
    d.rect(*E(-Wd / 2, BOARD_T), *E(Wd / 2, zmax), 0.25, (1.2, 0.8))
    d.circle(*E(0, zc), dia / 2, 0.35)
    d.dim_h(E(-Wd / 2, 0)[0], E(Wd / 2, 0)[0], E(0, zmin)[1], E(0, zmin)[1], E(0, zmin)[1] + 13, f"{Wd:.1f}")
    d.text(*E(0, zmax - 5), f"component side {top:.0f}", 2.2, "middle")
    d.text(*E(0, zmin - 3.5), f"copper side {BOTTOM_H:.0f}", 2.2, "middle")
    k = dia / 2 * 0.7071
    d.arrow(*E(0, zc), *E(-k, zc - k), 0.18)
    d.arrow(*E(0, zc), *E(k, zc + k), 0.18)
    d.text(*E(k + 1.5, zc + k + 1.5), f"Ø {dia} min.", 2.5)
    return L, Wd, zmax - zmin, dia


def envelope(b, out_pdf, out_svg):
    text = (b["dir"] / f"{b['stem']}.kicad_pcb").read_text(encoding="utf-8")
    # drawing sheet, A4 landscape
    d = Drawing(297.0, 210.0)
    d.rect(10, 10, 287, 200, 0.35)
    L, Wd, H, dia = envelope_views(d, text, (55.0, 30.0), 135.0, (236.0, 105.0))
    notes = [
        "Dimensions in millimetres. Heights are above the board, for the parts listed in VNT-002.",
        f"Board {L:.0f} × {Wd:.0f} × {BOARD_T} mm, same outline and M3 hole pattern as the sensor board.",
        f"Envelope {L + 2 * PLUG:.0f} × {Wd:.0f} × {H:.1f} mm with {PLUG:.0f} mm at each end for the plugs.",
        f"A round tube needs an inner diameter of at least {dia} mm; allow 2 mm more.",
        "Battery lead and panel wires leave at the left end, the sensor cable at the right end.",
        "U1, U2: INA226 module standing in an 8.5 mm socket; 39 mm covers a 27 mm module.",
        "M1: CN3791 module on 8.5 mm sockets, within 44 × 28 mm.",
    ]
    for i, n in enumerate(notes):
        d.text(14, 163 + i * 4.6, n, 2.6)
    d.rect(200, 172, 287, 200, 0.35)
    d.line(200, 181, 287, 181, 0.25)
    d.line(200, 190, 287, 190, 0.25)
    d.line(255, 190, 255, 200, 0.25)
    d.text(203, 178.5, "Team sevenUP", 3.2, bold=True)
    d.text(203, 187.5, f"Vantage — {b['title']}, module envelope", 3.0)
    d.text(203, 197, "Date 2026-11-05", 2.8)
    d.text(258, 197, "Rev B   1:1", 2.8)
    d.pdf(out_pdf, f"Vantage, {b['title']}, module envelope")
    # document figure, portrait, 1:1 within the 176 mm text width
    f = Drawing(176.0, 208.0)
    envelope_views(f, text, (40.0, 12.0), 109.0, (88.0, 166.0))
    out_svg.write_text(f.svg("power_envelope"), encoding="utf-8")


def main():
    if not shutil.which(CLI):
        sys.exit("kicad-cli not found: install KiCad or set KICAD_CLI to its path")
    keys = sys.argv[1:] or list(BOARDS)
    for key in keys:
        b = BOARDS[key]
        b["out"].mkdir(parents=True, exist_ok=True)
        stem = b["stem"]
        run(CLI, "sch", "export", "pdf", "-o", b["out"] / f"{stem}_Schematic.pdf", b["dir"] / f"{stem}.kicad_sch")
        with tempfile.TemporaryDirectory() as tmp:
            artwork(b, tmp, "USLetter", b["out"] / f"{stem}_Copper-Artwork_Letter.pdf")
            artwork(b, tmp, "A4", b["out"] / f"{stem}_Copper-Artwork_A4.pdf")
            assembly_drawing(b, tmp, b["out"] / f"{stem}_Assembly-Drawing.pdf")
            figures(b, key, tmp)
        if key == "power":
            envelope(b, b["out"] / f"{stem}_Envelope.pdf", FIG / "power_envelope.svg")
    print("outputs written")


if __name__ == "__main__":
    main()
