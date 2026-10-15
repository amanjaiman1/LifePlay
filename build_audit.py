#!/usr/bin/env python3
"""
Build the 10-Day Personal Performance Audit — a print-ready A4 PDF logbook.

    python build_audit.py                 # writes 10_Day_Personal_Performance_Audit.pdf
    python build_audit.py --out my.pdf    # custom output path

Edit the CONFIG block below to change labels, habits, prompts or to pre-print
your own targets. Leave a pre-fill value as "" to keep the field blank for
handwriting. Requires: reportlab (pip install reportlab).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# =============================================================================
# CONFIG — safe to edit
# =============================================================================
CONFIG = {
    "output": "10_Day_Personal_Performance_Audit.pdf",
    "days": 10,
    "title": "10-DAY PERFORMANCE AUDIT",
    "subtitle": "Personal Discipline, Deep Work, Physical Training & Recovery",

    # Optional pre-printed values. "" = blank field for handwriting.
    "prefill": {
        "name": "",
        "start_date": "",            # ISO format, e.g. "2026-10-19": fills every daily date + weekday
        "focus_target_min": "",      # e.g. "240"
        "run_target_km_per_run": "", # e.g. "5"
        "run_target_km_total": "",   # e.g. "25"
        "target_bedtime": "",        # e.g. "22:30"
        "target_wake": "",           # e.g. "06:00"
        "time_window_min": "",       # tolerance for "within my planned time window", e.g. "30"
    },

    # Number of rows in the daily focused-work table (minimum 5 recommended).
    "work_sessions": 5,

    # Supporting habits (the primary priority is tracked separately on every page).
    "habits": [
        "Woke up within my planned time window.",
        "Began my first important task without unnecessary delay.",
        "Followed my planned study/work schedule.",
        "Avoided unnecessary social media or entertainment during work.",
        "Followed my planned physical activity or recovery schedule.",
        "Prepared the next day's priorities.",
        "Went to bed within my planned time window.",
    ],

    "review_prompts": [
        "What was my biggest meaningful achievement today?",
        "Where did I waste the most time or break discipline?",
        "What was the main reason for any missed target?",
        "What did I learn about my own behaviour today?",
        "What is the single most important correction for tomorrow?",
    ],
}

# =============================================================================
# Geometry (all values in millimetres, measured from the TOP-LEFT of the page)
# =============================================================================
PAGE_W, PAGE_H = 210.0, 297.0
ML = 12.0                      # left margin
MR = 12.0                      # right margin
CW = PAGE_W - ML - MR          # content width = 186 mm
TOP = 10.0                     # content starts here
BOTTOM = 284.0                 # content must end above this line
FOOTER_RULE = 287.2
FOOTER_BASE = 290.6

# Monochrome palette (grey levels: 0 = black, 1 = white)
INK = 0.0
DARK = 0.16       # labels
MID = 0.38        # hints, units
RULE = 0.55       # cell borders
FAINT = 0.78      # guide lines
FILL = 0.925      # header fills
FILL_SOFT = 0.965

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")


def _register_fonts():
    """Register IBM Plex Sans Condensed (OFL). Fall back to Helvetica if missing."""
    files = {
        "R": "IBMPlexSansCondensed-Regular.ttf",
        "M": "IBMPlexSansCondensed-Medium.ttf",
        "SB": "IBMPlexSansCondensed-SemiBold.ttf",
        "B": "IBMPlexSansCondensed-Bold.ttf",
        "I": "IBMPlexSansCondensed-Italic.ttf",
    }
    fonts = {}
    try:
        for key, fname in files.items():
            name = "Plex-" + key
            pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fname)))
            fonts[key] = name
    except Exception as exc:  # pragma: no cover - fallback path
        print(f"[warn] Plex fonts unavailable ({exc}); falling back to Helvetica.")
        fonts = {"R": "Helvetica", "M": "Helvetica", "SB": "Helvetica-Bold",
                 "B": "Helvetica-Bold", "I": "Helvetica-Oblique"}
    return fonts


F = _register_fonts()


# =============================================================================
# Drawing toolkit
# =============================================================================
class PDF:
    def __init__(self, path: str, total_pages: int):
        self.c = canvas.Canvas(path, pagesize=(PAGE_W * mm, PAGE_H * mm))
        self.c.setTitle("10-Day Personal Performance Audit")
        self.c.setAuthor("LifePlay")
        self.c.setSubject("Personal discipline, deep work, physical training & recovery log")
        self.c.setCreator("build_audit.py (ReportLab)")
        self.total = total_pages
        self.page = 0
        self.warnings: list[str] = []
        self.max_y = 0.0
        self.page_name = ""

    # ---- coordinates -------------------------------------------------------
    @staticmethod
    def X(x):
        return x * mm

    @staticmethod
    def Y(y):
        return (PAGE_H - y) * mm

    def track(self, y):
        self.max_y = max(self.max_y, y)

    # ---- primitives ----------------------------------------------------------
    def grey(self, g, stroke=True, fill=True):
        if stroke:
            self.c.setStrokeGray(g)
        if fill:
            self.c.setFillGray(g)

    def line(self, x1, y1, x2, y2, w=0.45, g=RULE, dash=None):
        c = self.c
        c.setLineWidth(w)
        c.setStrokeGray(g)
        c.setDash(dash) if dash else c.setDash()
        c.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2))
        c.setDash()
        self.track(max(y1, y2))

    def rect(self, x, y, w, h, lw=0.45, g=RULE, fill=None, stroke=True, radius=0):
        c = self.c
        c.setLineWidth(lw)
        c.setStrokeGray(g)
        if fill is not None:
            c.setFillGray(fill)
        if radius:
            c.roundRect(self.X(x), self.Y(y + h), w * mm, h * mm, radius * mm,
                        stroke=1 if stroke else 0, fill=1 if fill is not None else 0)
        else:
            c.rect(self.X(x), self.Y(y + h), w * mm, h * mm,
                   stroke=1 if stroke else 0, fill=1 if fill is not None else 0)
        self.track(y + h)

    def width(self, s, font, size, tracking=0.0):
        return pdfmetrics.stringWidth(s, font, size) / mm + tracking * max(len(s) - 1, 0) / mm

    def fit(self, s, font, size, max_w, min_size=6.2, tracking=0.0, where=""):
        """Return a font size at which `s` fits `max_w`; record a warning if impossible."""
        sz = size
        while self.width(s, font, sz, tracking) > max_w and sz > min_size:
            sz = round(sz - 0.1, 2)
        if self.width(s, font, sz, tracking) > max_w + 0.05:
            self.warnings.append(f"p{self.page} overflow: '{s}' ({where})")
        return sz

    def text(self, x, y, s, font=None, size=7.0, g=INK, align="left", tracking=0.0,
             max_w=None, min_size=6.2):
        """Draw text with its BASELINE at y (top-down mm)."""
        font = font or F["R"]
        if max_w is not None:
            size = self.fit(s, font, size, max_w, min_size, tracking, where=self.page_name)
        w = self.width(s, font, size, tracking)
        if align == "center":
            x = x - w / 2
        elif align == "right":
            x = x - w
        c = self.c
        c.setFillGray(g)
        t = c.beginText()
        t.setTextOrigin(self.X(x), self.Y(y))
        t.setFont(font, size)
        t.setCharSpace(tracking)
        t.textOut(s)
        c.drawText(t)
        self.track(y)
        return w

    def wrap(self, s, font, size, max_w):
        words, lines, cur = s.split(), [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if self.width(trial, font, size) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, max_w, font=None, size=7.5, leading=None, g=INK, max_lines=None):
        """Draw a wrapped paragraph; y = first baseline. Returns y of the next baseline."""
        font = font or F["R"]
        leading = leading or size * 1.32 * 0.3528
        lines = self.wrap(s, font, size, max_w)
        if max_lines and len(lines) > max_lines:
            self.warnings.append(f"p{self.page} paragraph truncated: '{s[:40]}...'")
            lines = lines[:max_lines]
        for ln in lines:
            self.text(x, y, ln, font, size, g)
            y += leading
        return y

    def rich_para(self, x, y, runs, max_w, size=7.5, leading=None):
        """Wrapped paragraph made of (text, font, grey) runs. Returns next baseline."""
        leading = leading or size * 1.32 * 0.3528
        tokens = []
        for txt, font, g in runs:
            for i, wd in enumerate(txt.split(" ")):
                if wd == "":
                    continue
                tokens.append((wd, font, g))
        line, line_w = [], 0.0
        space = self.width(" ", F["R"], size)

        def flush(ln, yy):
            xx = x
            for wd, fnt, gg in ln:
                self.text(xx, yy, wd, fnt, size, gg)
                xx += self.width(wd, fnt, size) + space

        for wd, fnt, g in tokens:
            ww = self.width(wd, fnt, size)
            if line and line_w + space + ww > max_w:
                flush(line, y)
                y += leading
                line, line_w = [], 0.0
            line_w = line_w + (space if line else 0) + ww
            line.append((wd, fnt, g))
        if line:
            flush(line, y)
            y += leading
        return y

    # ---- form components ---------------------------------------------------------
    def checkbox(self, x, y_mid, size=2.9, lw=0.6):
        self.rect(x, y_mid - size / 2, size, size, lw=lw, g=INK)

    def options(self, x, y_mid, labels, size=2.9, font=None, fsize=6.6, gap=2.6, g=INK):
        """Row of [ ] LABEL checkboxes. Returns x after the last label."""
        font = font or F["SB"]
        for lab in labels:
            self.checkbox(x, y_mid, size)
            x += size + 1.0
            x += self.text(x, y_mid + fsize * 0.3528 * 0.36, lab, font, fsize, g) + gap
        return x - gap

    def options_width(self, labels, size=2.9, font=None, fsize=6.6, gap=2.6):
        font = font or F["SB"]
        return sum(size + 1.0 + self.width(l, font, fsize) for l in labels) + gap * (len(labels) - 1)

    def rating(self, x, y_mid, values, pitch=4.4, r=1.75, fsize=6.4, prefill=None):
        """Numbers inside light circles — circle one. Returns x after the scale."""
        for i, v in enumerate(values):
            cx = x + r + i * pitch
            self.c.setLineWidth(0.4)
            self.c.setStrokeGray(MID)
            self.c.circle(self.X(cx), self.Y(y_mid), r * mm, stroke=1, fill=0)
            self.text(cx, y_mid + fsize * 0.3528 * 0.35, str(v), F["M"], fsize, DARK, align="center")
        return x + (len(values) - 1) * pitch + 2 * r

    def cell(self, x, y, w, h, label=None, unit=None, lw=0.45, g=RULE, fill=None,
             lsize=6.3, label_font=None, label_g=DARK, value=None, value_size=10):
        """Bordered field with a small label top-left and optional unit bottom-right."""
        self.rect(x, y, w, h, lw=lw, g=g, fill=fill)
        if label:
            self.text(x + 1.3, y + 2.65, label, label_font or F["SB"], lsize, label_g,
                      tracking=0.15, max_w=w - 2.6 - (self.width(unit, F["R"], 6.3) + 1.5 if unit and h < 6 else 0),
                      min_size=6.2)
        if unit:
            self.text(x + w - 1.3, y + h - 1.35, unit, F["R"], 6.4, MID, align="right")
        if value:
            self.text(x + 2.0, y + h - 1.7, str(value), F["M"], value_size, INK, max_w=w - 4)

    def section(self, y, letter, title, hint="", x=ML, w=CW):
        """Strong section header: black tab with letter, bold title, grey hint, rule."""
        h = 5.0
        self.rect(x, y, h, h, lw=0, g=INK, fill=INK, stroke=False)
        self.text(x + h / 2, y + 3.55, letter, F["B"], 8.6, 1.0, align="center")
        tw = self.text(x + h + 2.0, y + 3.6, title, F["B"], 8.8, INK, tracking=0.55)
        if hint:
            hx = x + h + 2.0 + tw + 4.0
            self.text(x + w, y + 3.55, hint, F["I"], 6.6, MID, align="right",
                      max_w=x + w - hx, min_size=6.2)
        self.line(x, y + h, x + w, y + h, w=0.9, g=INK)
        return y + h

    def footer(self, left):
        self.line(ML, FOOTER_RULE, PAGE_W - MR, FOOTER_RULE, w=0.35, g=FAINT)
        self.text(ML, FOOTER_BASE, left, F["SB"], 6.4, MID, tracking=0.35)
        self.text(PAGE_W / 2, FOOTER_BASE, "Record reality, not intention  \u00b7  Missing data = N/R",
                  F["I"], 6.4, MID, align="center")
        self.text(PAGE_W - MR, FOOTER_BASE, f"PAGE {self.page} OF {self.total}", F["SB"], 6.4, MID,
                  align="right", tracking=0.35)

    def new_page(self, name):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.page_name = name
        self.max_y = 0.0

    def finish_page(self, footer_left):
        # content must stay above BOTTOM (the footer is drawn afterwards)
        if self.max_y > BOTTOM + 0.01:
            self.warnings.append(f"p{self.page} ({self.page_name}) content ends at {self.max_y:.1f} mm > {BOTTOM} mm")
        self.footer(footer_left)

    def save(self):
        self.c.showPage()
        self.c.save()


# =============================================================================
# Helpers for pre-filled values
# =============================================================================
def pf(key):
    return (CONFIG.get("prefill", {}).get(key) or "").strip()


def start_date():
    s = pf("start_date")
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        print(f"[warn] prefill.start_date '{s}' is not ISO (YYYY-MM-DD); ignoring.")
        return None


WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


# =============================================================================
# DAILY LOG PAGE
# =============================================================================
def daily_page(p: PDF, day: int):
    p.new_page(f"Day {day:02d}")
    n_days = CONFIG["days"]
    sd = start_date()
    the_date = sd + dt.timedelta(days=day - 1) if sd else None

    # ---------------- Header: DAY badge + A. DAILY IDENTIFICATION ----------------
    y = TOP
    badge_w, row_h = 27.0, 8.2
    bh = 5.0 + 1.0 + 2 * row_h
    p.rect(ML, y, badge_w, bh, lw=0, g=INK, fill=INK, stroke=False)
    p.text(ML + badge_w / 2, y + 5.4, "DAY", F["B"], 7.8, 1.0, align="center", tracking=1.8)
    p.text(ML + badge_w / 2, y + 15.6, f"{day:02d}", F["B"], 27, 1.0, align="center")
    p.text(ML + badge_w / 2, y + 19.9, f"OF {n_days:02d}", F["SB"], 6.4, 0.82, align="center", tracking=1.0)

    x0 = ML + badge_w + 2.4
    aw = PAGE_W - MR - x0
    p.section(y, "A", "DAILY IDENTIFICATION",
              "Morning: date, sleep, wake-up, planned bedtime.  Next morning: actual bedtime.", x=x0, w=aw)
    y += 6.0
    # Row 1
    r1 = y
    w_date, w_dow = 38.0, 74.0
    w_wake = aw - w_date - w_dow
    p.cell(x0, r1, w_date, row_h, "DATE", value=the_date.strftime("%d %b %Y") if the_date else None)
    p.cell(x0 + w_date, r1, w_dow, row_h, "DAY OF THE WEEK \u2014 CIRCLE ONE")
    dx = x0 + w_date + 3.0
    pitch = (w_dow - 6.0) / 7
    for i, wd in enumerate(WEEKDAYS):
        cx = dx + pitch * (i + 0.5)
        p.text(cx, r1 + 6.6, wd, F["SB"], 6.8, DARK, align="center", tracking=0.3)
        if the_date and the_date.weekday() == i:
            p.c.setLineWidth(0.7)
            p.c.setStrokeGray(INK)
            p.c.ellipse(p.X(cx - 4.2), p.Y(r1 + 7.8), p.X(cx + 4.2), p.Y(r1 + 3.9), stroke=1, fill=0)
    p.cell(x0 + w_date + w_dow, r1, w_wake, row_h, "ACTUAL WAKE-UP TIME", unit="hh:mm")
    # Row 2
    r2 = y + row_h
    w_sleep, w_pb = 58.0, 46.0
    w_ab = aw - w_sleep - w_pb
    p.cell(x0, r2, w_sleep, row_h, "PREVIOUS NIGHT'S SLEEP DURATION")
    sx = x0 + 1.5
    p.text(sx + 10.5, r2 + 6.9, "h", F["R"], 6.6, MID)
    p.text(sx + 24.5, r2 + 6.9, "min", F["R"], 6.6, MID)
    p.options(x0 + w_sleep - 15.6, r2 + 5.8, ["M", "E"], size=2.6, fsize=6.2, gap=1.8)
    p.cell(x0 + w_sleep, r2, w_pb, row_h, "PLANNED BEDTIME (TONIGHT)", unit="hh:mm",
           value=pf("target_bedtime") or None)
    p.cell(x0 + w_sleep + w_pb, r2, w_ab, row_h, "ACTUAL BEDTIME \u2014 FILL NEXT MORNING", unit="hh:mm")
    p.rect(x0, r1, aw, 2 * row_h, lw=0.7, g=INK)
    y = TOP + bh + 2.0

    # ---------------- B. FOCUSED WORK AND STUDY ----------------
    y = p.section(y, "B", "FOCUSED WORK & STUDY",
                  "Focused minutes = NET minutes of genuine, intentional work. Exclude breaks, unrelated browsing, scrolling and idle desk time.")
    y += 1.0
    tw = 128.0
    cols = [("WORK|SESSION", 11.0), ("SUBJECT / TASK", 45.0), ("START|hh:mm", 13.0), ("END|hh:mm", 13.0),
            ("FOCUSED|MIN (NET)", 15.0), ("QUALITY|1\u20135", 13.0), ("DISTRACTIONS|COUNT", 18.0)]
    assert abs(sum(w for _, w in cols) - tw) < 0.01
    th, rh = 5.8, 6.6
    n_rows = CONFIG["work_sessions"]
    # header row
    p.rect(ML, y, tw, th, lw=0.45, g=RULE, fill=FILL)
    cx = ML
    for lab, w in cols:
        parts = lab.split("|")
        if len(parts) == 1:
            p.text(cx + w / 2, y + 3.75, parts[0], F["SB"], 6.4, DARK, align="center", tracking=0.1, max_w=w - 1.0)
        else:
            p.text(cx + w / 2, y + 2.55, parts[0], F["SB"], 6.4, DARK, align="center", tracking=0.1, max_w=w - 1.0)
            p.text(cx + w / 2, y + 4.9, parts[1], F["SB"], 6.4, DARK, align="center", tracking=0.1, max_w=w - 1.0)
        cx += w
    ty = y + th
    for i in range(n_rows):
        p.rect(ML, ty + i * rh, tw, rh, lw=0.45, g=RULE)
        p.text(ML + cols[0][1] / 2, ty + i * rh + rh / 2 + 1.0, str(i + 1), F["B"], 8, MID, align="center")
    # vertical lines
    cx = ML
    for _, w in cols[:-1]:
        cx += w
        p.line(cx, y, cx, ty + n_rows * rh, w=0.45, g=RULE)
    p.rect(ML, y, tw, th + n_rows * rh, lw=0.7, g=INK)
    table_bottom = ty + n_rows * rh
    # summary panel
    sx = ML + tw + 3.0
    sw = PAGE_W - MR - sx
    ph = (table_bottom - y) / 4
    half = sw / 2
    p.cell(sx, y, half, ph, "TOTAL FOCUSED", unit="min")
    p.cell(sx + half, y, half, ph, "TOTAL FOCUSED", unit="h")
    p.cell(sx, y + ph, half, ph, "PLANNED FOCUSED", unit="min", value=pf("focus_target_min") or None)
    p.cell(sx + half, y + ph, half, ph, "MOST PRODUCTIVE #", unit="session")
    p.cell(sx, y + 2 * ph, sw, ph, "FOCUS TARGET ACHIEVED? (TOTAL \u2265 PLANNED)")
    p.options(sx + 1.5, y + 2 * ph + ph - 3.0, ["YES", "NO"], gap=6)
    p.cell(sx, y + 3 * ph, sw, ph, "MAIN DISTRACTION")
    p.rect(sx, y, sw, 4 * ph, lw=0.7, g=INK)
    y = table_bottom + 1.2
    p.cell(ML, y, CW, 8.2, "ONE TASK COMPLETED THAT MATERIALLY ADVANCED MY GOALS")
    y += 8.2 + 2.0

    # ---------------- C. PHYSICAL TRAINING AND RUNNING ----------------
    y = p.section(y, "C", "PHYSICAL TRAINING & RUNNING",
                  "Never train through pain, illness or excessive fatigue. Choosing recovery is not a discipline failure.")
    y += 1.0
    h = 8.2
    widths = [33.0, 31.0, 24.0, 30.0]
    xx = ML
    p.cell(xx, y, widths[0], h, "RUNNING COMPLETED?")
    p.options(xx + 1.5, y + h - 2.6, ["YES", "NO"], gap=4)
    xx += widths[0]
    p.cell(xx, y, widths[1], h, "RUNNING DISTANCE", unit="km")
    p.options(xx + 1.5, y + h - 2.6, ["M", "E"], size=2.6, fsize=6.2, gap=1.8)
    xx += widths[1]
    p.cell(xx, y, widths[2], h, "RUNNING DURATION", unit="min")
    xx += widths[2]
    p.cell(xx, y, widths[3], h, "AVERAGE PACE, IF KNOWN", unit="min/km")
    xx += widths[3]
    rw = PAGE_W - MR - xx
    p.cell(xx, y, rw, h, "PERCEIVED EFFORT (RPE)  1 = VERY EASY \u00b7 10 = MAXIMAL")
    p.rating(xx + 2.0, y + h - 2.75, list(range(1, 11)), pitch=(rw - 4.0 - 3.5) / 9)
    y += h
    widths = [62.0, 26.0, 34.0]
    xx = ML
    p.cell(xx, y, widths[0], h, "OTHER PHYSICAL ACTIVITY \u2014 TYPE")
    xx += widths[0]
    p.cell(xx, y, widths[1], h, "DURATION, APPROX.", unit="min")
    xx += widths[1]
    p.cell(xx, y, widths[2], h, "MOBILITY / STRETCHING?")
    p.options(xx + 1.5, y + h - 2.6, ["YES", "NO"], gap=4)
    xx += widths[2]
    p.cell(xx, y, PAGE_W - MR - xx, h, "UNUSUAL FATIGUE, PAIN OR DISCOMFORT")
    ox = p.options(xx + 1.5, y + h - 2.6, ["NONE", "YES \u2192 NOTE:"], gap=3)
    y += h
    xx = ML
    p.cell(xx, y, 33.0, h, "REST OR RECOVERY DAY?")
    p.options(xx + 1.5, y + h - 2.6, ["YES", "NO"], gap=4)
    xx += 33.0
    p.cell(xx, y, PAGE_W - MR - xx, h, "IF NO PLANNED TRAINING WAS DONE TODAY, IT WAS \u2014 TICK ONE")
    labels = ["PLANNED REST (in 10-day plan)", "RECOVERY CHOICE (pain / illness / fatigue)",
              "UNPLANNED MISS (planned, not done)"]
    p.options(xx + 1.5, y + h - 2.6, labels, gap=5.0, fsize=6.5)
    p.rect(ML, y - 2 * h, CW, 3 * h, lw=0.7, g=INK)
    y += h + 2.0

    # ---------------- D. DAILY DISCIPLINE AND HABITS ----------------
    y = p.section(y, "D", "DAILY DISCIPLINE & HABITS",
                  "Tick one per row: DONE \u00b7 PARTIAL \u00b7 MISSED.  Not recorded \u2192 write N/R.  Habits are not equally important.")
    y += 1.0
    ph = 8.6
    opt_labels = ["DONE", "PARTIAL", "MISSED"]
    ow = p.options_width(opt_labels, gap=4.0)
    p.cell(ML, y, CW, ph, "PRIMARY PRIORITY \u2014 THE ONE TASK THAT MAKES TODAY A SUCCESS (WRITE IT BEFORE STARTING WORK)",
           lw=1.1, g=INK, label_font=F["B"], label_g=INK)
    p.line(PAGE_W - MR - ow - 5.0, y, PAGE_W - MR - ow - 5.0, y + ph, w=0.45, g=RULE)
    p.text(PAGE_W - MR - ow - 2.5, y + 2.65, "COMPLETED MY PRIMARY PRIORITY?", F["SB"], 6.4, DARK, tracking=0.15)
    p.options(PAGE_W - MR - ow - 2.5, y + ph - 2.7, opt_labels, gap=4.0)
    y += ph + 1.2
    # habits in two columns
    colw = (CW - 3.0) / 2
    box_col = 10.4
    hh = 3.9
    rows = (len(CONFIG["habits"]) + 2) // 2
    habit_h = 6.2
    for col in range(2):
        cx0 = ML + col * (colw + 3.0)
        p.rect(cx0, y, colw, hh, lw=0, g=RULE, fill=FILL, stroke=False)
        p.text(cx0 + 1.3, y + 2.8, "SUPPORTING HABITS", F["SB"], 6.4, DARK, tracking=0.3)
        for k, lab in enumerate(opt_labels):
            bx = cx0 + colw - 3 * box_col + k * box_col + box_col / 2
            p.text(bx, y + 2.8, lab, F["SB"], 6.3, DARK, align="center", tracking=0.0)
    yy = y + hh
    for i, habit in enumerate(CONFIG["habits"]):
        col, r = (0, i) if i < rows else (1, i - rows)
        cx0 = ML + col * (colw + 3.0)
        ry = yy + r * habit_h
        p.line(cx0, ry + habit_h, cx0 + colw, ry + habit_h, w=0.4, g=RULE)
        p.text(cx0 + 1.2, ry + 3.9, f"{i + 1}", F["B"], 7.0, MID)
        tx = cx0 + 4.6
        tmax = colw - 3 * box_col - 5.6
        lines = p.wrap(habit, F["R"], 7.0, tmax)
        if len(lines) == 1:
            p.text(tx, ry + 3.95, lines[0], F["R"], 7.0, INK)
        else:
            p.text(tx, ry + 2.75, lines[0], F["R"], 7.0, INK)
            p.text(tx, ry + 5.3, " ".join(lines[1:]), F["R"], 7.0, INK, max_w=tmax)
        for k in range(3):
            bx = cx0 + colw - 3 * box_col + k * box_col + box_col / 2
            p.checkbox(bx - 1.45, ry + habit_h / 2)
    # legend in the free cell
    free = len(CONFIG["habits"]) - rows
    if free < rows:
        cx0 = ML + colw + 3.0
        ry = yy + free * habit_h
        p.para(cx0 + 1.2, ry + 2.9, "Bedtime habit (7): tick it next morning. If a habit did not apply "
               "today, write N/A and exclude it from the 10-day count.", colw - 2.4, F["I"], 6.3, g=MID)
    y = yy + rows * habit_h + 2.0

    # ---------------- E. TIME AND DIGITAL DISTRACTION AUDIT ----------------
    y = p.section(y, "E", "TIME & DIGITAL DISTRACTION AUDIT",
                  "Values are ESTIMATES unless read from device statistics \u2014 tick M (measured) or E (estimated).")
    y += 1.0
    h = 8.2
    qw = CW / 4
    items = [("RECREATIONAL SCREEN TIME", "min", True), ("UNPLANNED SCROLLING", "min", True),
             ("SIGNIFICANT INTERRUPTIONS", "count", False), ("TIME LOST TO AVOIDABLE ACTIVITIES", "min", True)]
    for i, (lab, unit, me) in enumerate(items):
        xx = ML + i * qw
        p.cell(xx, y, qw, h, lab, unit=unit)
        if me:
            p.options(xx + 1.5, y + h - 2.6, ["M", "E"], size=2.6, fsize=6.2, gap=1.8)
    y += h
    p.cell(ML, y, CW / 2, h, "BIGGEST SOURCE OF WASTED TIME")
    p.cell(ML + CW / 2, y, CW / 2, h, "ONE SPECIFIC ACTION TO REDUCE THIS WASTE TOMORROW")
    p.rect(ML, y - h, CW, 2 * h, lw=0.7, g=INK)
    y += h + 2.0

    # ---------------- F. ENERGY, MOOD AND RECOVERY ----------------
    y = p.section(y, "F", "ENERGY, MOOD & RECOVERY",
                  "Circle 1\u20135: 1 = very low, 5 = very high (stress: 5 = most stressed). A tracking tool, not a medical assessment.")
    y += 1.0
    ratings = ["MORNING ENERGY", "CONCENTRATION QUALITY", "MOOD", "PHYSICAL FRESHNESS",
               "STRESS LEVEL (5 = HIGH)", "SLEEP QUALITY"]
    rw6 = CW / len(ratings)
    for i, lab in enumerate(ratings):
        xx = ML + i * rw6
        p.cell(xx, y, rw6, h, lab)
        p.rating(xx + (rw6 - (4 * 4.4 + 3.5)) / 2, y + h - 2.75, [1, 2, 3, 4, 5])
    y += h
    xx = ML
    p.cell(xx, y, 28.0, h, "SLEEP DURATION", unit="h")
    xx += 28.0
    p.cell(xx, y, 24.0, h, "WATER, APPROX.", unit="litres")
    xx += 24.0
    p.cell(xx, y, 57.0, h, "MEALS REASONABLY CONSISTENT WITH MY NEEDS?")
    p.options(xx + 1.5, y + h - 2.6, ["YES", "NO"], gap=4)
    xx += 57.0
    p.cell(xx, y, PAGE_W - MR - xx, h, "ANY FACTOR AFFECTING TODAY'S PERFORMANCE")
    p.rect(ML, y - h, CW, 2 * h, lw=0.7, g=INK)
    y += h + 2.0

    # ---------------- G. DAILY SELF-REVIEW ----------------
    y = p.section(y, "G", "DAILY SELF-REVIEW",
                  "Short, factual answers. The self-assessment is subjective \u2014 justify it with evidence from this page.")
    y += 1.0
    qh = 8.2
    for i, q in enumerate(CONFIG["review_prompts"]):
        p.cell(ML, y, CW, qh, None)
        p.text(ML + 1.3, y + 2.75, f"{i + 1}", F["B"], 6.6, INK)
        p.text(ML + 4.0, y + 2.75, q, F["SB"], 6.6, DARK, max_w=CW - 6)
        y += qh
    p.rect(ML, y - qh * len(CONFIG["review_prompts"]), CW, qh * len(CONFIG["review_prompts"]), lw=0.7, g=INK)
    y += 1.2
    h = 8.2
    xx = ML
    w_sa = 76.0
    p.cell(xx, y, w_sa, h, "DAILY SELF-ASSESSMENT (1\u201310) \u2014 SUBJECTIVE")
    p.rating(xx + 2.0, y + h - 2.75, list(range(1, 11)), pitch=(w_sa - 4.0 - 3.5) / 9)
    xx += w_sa
    p.cell(xx, y, 44.0, h, "WAS THIS SCORE BASED ON EVIDENCE?")
    p.options(xx + 1.5, y + h - 2.6, ["YES", "NO"], gap=4)
    xx += 44.0
    p.cell(xx, y, PAGE_W - MR - xx, h, "SIGNATURE / PERSONAL ACCOUNTABILITY MARK")
    y += h
    p.cell(ML, y, CW, h, "ONE SENTENCE EXPLAINING THE SCORE")
    p.rect(ML, y - h, CW, 2 * h, lw=0.7, g=INK)
    y += h
    p.track(y)
    p.finish_page(f"DAILY LOG  \u00b7  DAY {day:02d} OF {n_days:02d}")


# =============================================================================
# Shared page furniture for setup / summary / analysis pages
# =============================================================================
def page_head(p: PDF, kicker: str, title: str, right: str = "", subtitle: str = "", big=False):
    """Kicker line + heavy rule + large title. Returns y below the block."""
    y = TOP
    p.text(ML, y + 3.2, kicker, F["SB"], 7.4, INK, tracking=1.4)
    if right:
        p.text(PAGE_W - MR, y + 3.2, right, F["SB"], 7.0, MID, align="right", tracking=0.9)
    p.line(ML, y + 5.0, PAGE_W - MR, y + 5.0, w=1.8, g=INK)
    if big:
        p.text(ML, y + 19.5, title, F["B"], 30, INK, tracking=0.6, max_w=CW)
        y += 19.5
        if subtitle:
            p.text(ML, y + 7.2, subtitle, F["M"], 12.5, DARK, max_w=CW)
            y += 7.2
    else:
        p.text(ML, y + 14.2, title, F["B"], 19, INK, tracking=0.5, max_w=CW)
        y += 14.2
        if subtitle:
            p.text(ML, y + 5.4, subtitle, F["I"], 8.2, MID, max_w=CW)
            y += 5.4
    return y + 3.5


def guide_lines(p: PDF, x, y, w, h, n, top_pad=4.2):
    """Faint handwriting guide lines inside a cell."""
    if n <= 0:
        return
    step = (h - top_pad) / n
    for i in range(1, n + 1):
        yy = y + top_pad + step * i - 0.9
        if yy < y + h - 0.6:
            p.line(x + 1.3, yy, x + w - 1.3, yy, w=0.3, g=FAINT)


def text_cell(p: PDF, x, y, w, h, label, lines=1, unit=None, lw=0.45, g=RULE, value=None):
    p.cell(x, y, w, h, label, unit=unit, lw=lw, g=g, value=value)
    if lines > 1:
        guide_lines(p, x, y, w, h, lines)


# =============================================================================
# PAGE 1 — PERSONAL PERFORMANCE MISSION
# =============================================================================
def mission_page(p: PDF):
    p.new_page("Mission")
    y = page_head(p, "PERSONAL PERFORMANCE MISSION", CONFIG["title"], right="SETUP \u00b7 COMPLETE BEFORE DAY 1",
                  subtitle=CONFIG["subtitle"], big=True)
    p.text(ML, y + 1.6, "A ten-day accountability log: one page per day, three to five minutes, evidence over emotion.",
           F["I"], 8.6, MID)
    y += 6.5

    y = p.section(y, "1", "IDENTIFICATION") + 1.2
    h = 13.0
    sd = start_date()
    ed = sd + dt.timedelta(days=CONFIG["days"] - 1) if sd else None
    p.cell(ML, y, 96, h, "NAME OR CALLSIGN", value=pf("name") or None, value_size=12)
    p.cell(ML + 96, y, 45, h, "START DATE", value=sd.strftime("%d %b %Y") if sd else None)
    p.cell(ML + 141, y, 45, h, "END DATE (DAY 10)", value=ed.strftime("%d %b %Y") if ed else None)
    p.rect(ML, y, CW, h, lw=0.7, g=INK)
    y += h + 3.2

    y = p.section(y, "2", "MISSION", "Specific and observable \u2014 what will be different after 10 days?") + 1.2
    text_cell(p, ML, y, CW, 25.0, "PRIMARY OBJECTIVE FOR THESE 10 DAYS", lines=3)
    y += 25.0
    text_cell(p, ML, y, CW, 14.0, "MOST IMPORTANT AREA I WANT TO IMPROVE")
    p.rect(ML, y - 25.0, CW, 39.0, lw=0.7, g=INK)
    y += 14.0 + 3.2

    y = p.section(y, "3", "TARGETS", "Every daily YES / NO is judged against these. Set them realistically.") + 1.2
    h = 16.0
    w4 = CW / 4
    p.cell(ML, y, w4, h, "DAILY FOCUSED-WORK TARGET", unit="net min / day", value=pf("focus_target_min") or None,
           value_size=13)
    p.cell(ML + w4, y, w4, h, "RUNNING TARGET")
    rx = ML + w4 + 1.5
    p.text(rx, y + 9.0, pf("run_target_km_per_run") or "", F["M"], 10, INK)
    p.text(rx + 11.5, y + 9.0, "km per run", F["R"], 6.6, MID)
    p.text(rx, y + 14.4, pf("run_target_km_total") or "", F["M"], 10, INK)
    p.text(rx + 11.5, y + 14.4, "km in 10 days", F["R"], 6.6, MID)
    p.line(rx, y + 9.6, rx + 10.5, y + 9.6, w=0.35, g=FAINT)
    p.line(rx, y + 15.0, rx + 10.5, y + 15.0, w=0.35, g=FAINT)
    p.cell(ML + 2 * w4, y, w4, h, "TARGET BEDTIME", unit="hh:mm", value=pf("target_bedtime") or None, value_size=13)
    p.cell(ML + 3 * w4, y, w4, h, "TARGET WAKE-UP TIME", unit="hh:mm", value=pf("target_wake") or None, value_size=13)
    y += h
    h2 = 10.0
    p.cell(ML, y, CW / 2, h2, "PLANNED TIME WINDOW FOR BEDTIME AND WAKE-UP HABITS", unit="\u00b1 min",
           value=pf("time_window_min") or None)
    p.cell(ML + CW / 2, y, CW / 2, h2, "PLANNED RUNNING DAYS (REST DAYS ARE SCHEDULED ON PAGE 2)", unit="of 10 days")
    p.rect(ML, y - h, CW, h + h2, lw=0.7, g=INK)
    y += h2 + 3.2

    y = p.section(y, "4", "BEHAVIOUR", "Name a concrete action, not a personality trait.") + 1.2
    h = 21.0
    text_cell(p, ML, y, CW / 2, h, "ONE BEHAVIOUR I MUST ELIMINATE", lines=2)
    text_cell(p, ML + CW / 2, y, CW / 2, h, "ONE BEHAVIOUR I MUST STRENGTHEN", lines=2)
    p.rect(ML, y, CW, h, lw=0.7, g=INK)
    y += h + 3.2

    y = p.section(y, "5", "STANDING ORDERS", "Read once before Day 1. These rules apply to every page.") + 1.6
    # Core instruction — heavy box
    qh = 15.0
    p.rect(ML, y, CW, qh, lw=1.4, g=INK, fill=FILL_SOFT)
    p.rich_para(ML + 4, y + 6.0, [("Record reality, not intention.", F["B"], INK),
                                   ("Do not manipulate the numbers to make yourself look disciplined. "
                                    "An honest failure is more useful than a false success.", F["SB"], INK)],
                CW - 8, size=10.2, leading=4.6)
    y += qh + 2.2
    # N/R rule
    nh = 19.0
    p.rect(ML, y, CW, nh, lw=0.7, g=INK)
    p.rect(ML, y, 22, nh, lw=0, g=INK, fill=INK, stroke=False)
    p.text(ML + 11, y + 9.3, "N/R", F["B"], 13, 1.0, align="center")
    p.text(ML + 11, y + 13.6, "NOT RECORDED", F["SB"], 6.3, 0.85, align="center", tracking=0.4)
    p.rich_para(ML + 25, y + 4.6, [
        ("Missing data is marked N/R.", F["B"], INK),
        ("If you did not record a value, write N/R in the field. N/R is neither a success nor a failure: "
         "leave it out of every total, count and average, and state how many recorded days each figure is "
         "based on (n). A genuine zero \u2014 0 km on a rest day, 0 minutes of scrolling \u2014 is a recorded "
         "value: write 0, not N/R.", F["R"], INK)], CW - 28, size=8.0, leading=3.75)
    y += nh + 2.2
    bullets = [
        ("When to record.", "Morning, about 1 minute: Section A, the primary priority and planned focused minutes. "
         "Evening, about 3 minutes: Sections B\u2013G. Next morning: actual bedtime and habit 7."),
        ("Late entries.", "If a page is completed the next day, write LATE beside the date. Do not reconstruct "
         "details you cannot remember \u2014 use N/R."),
        ("Corrections.", "Strike through once and write the true value beside it. Never overwrite an entry to improve a result."),
        ("Evidence.", "Tick M when a value comes from a device, app or timer and E when it is your estimate. "
         "Ratings are self-reports, not measurements."),
    ]
    by = y + 3.6
    for head, body in bullets:
        p.rect(ML + 0.6, by - 2.0, 1.6, 1.6, lw=0, g=INK, fill=INK, stroke=False)
        by = p.rich_para(ML + 4.2, by, [(head, F["B"], INK), (body, F["R"], INK)], CW - 5, size=8.0, leading=3.75)
        by += 1.0
    y = by + 1.0

    y = p.section(y, "6", "COMMITMENT") + 1.2
    h = 14.0
    p.cell(ML, y, 110, h, "I WILL RECORD WHAT ACTUALLY HAPPENS FOR 10 CONSECUTIVE DAYS \u2014 SIGNATURE")
    p.cell(ML + 110, y, CW - 110, h, "DATE")
    p.rect(ML, y, CW, h, lw=0.7, g=INK)
    y += h
    p.finish_page("SETUP  \u00b7  PERSONAL PERFORMANCE MISSION")


# =============================================================================
# PAGE 2 — OPERATING RULES, MARKING KEY, DEFINITIONS, 10-DAY PLAN
# =============================================================================
DEFINITIONS = [
    ("Focused minutes (net)", "Genuine, intentional work on the stated task. Subtract breaks, unrelated browsing, "
     "scrolling, messaging and idle desk time. A 60-minute block with 15 minutes of drift = 45 focused minutes. "
     "Time at a desk is not focused time."),
    ("Work session", "One block of work on one task, from start to stop. Record its net focused minutes, not its clock length."),
    ("Session quality 1\u20135", "Depth of attention: 1 = constantly broken, 3 = mixed, 5 = deep and uninterrupted."),
    ("Distraction", "Any unplanned switch of attention away from the task (phone, browsing, chat). Tally each one in the session row."),
    ("Significant interruption", "An interruption that broke focus for about 5 minutes or more, or ended a session."),
    ("Primary priority", "The single task that would make the day a success, written before work starts. DONE only if "
     "completed to the standard you set; PARTIAL if meaningfully advanced but not finished."),
    ("Focus target achieved", "YES only if total net focused minutes \u2265 the planned focused minutes for that day."),
    ("Running completed", "A run actually performed, of any distance. Distance and pace from a watch or app = M; otherwise E."),
    ("Perceived effort (RPE)", "How hard the session felt, 1\u201310: 1 = very easy, 5 = steady, 7 = hard, 10 = maximal."),
    ("Planned rest / recovery choice / unplanned miss",
     "Planned rest: REST written in the 10-day plan below before the day began. Recovery choice: training reduced or "
     "skipped because of pain, illness or unusual fatigue \u2014 a sound decision, not a failure. Unplanned miss: "
     "training was planned, no health reason, not done."),
    ("Recreational screen time", "Phone, TV, gaming or computer use for entertainment or social media. Excludes work and study."),
    ("Unplanned scrolling", "Scrolling you did not intend to do. It is part of recreational screen time, not additional to it."),
    ("Time lost to avoidable activities", "Minutes spent on things you would not choose on reflection that displaced "
     "planned work, training or rest."),
    ("Sleep duration", "Time actually asleep the previous night, not time in bed. Write decimal hours in F (7 h 30 min = 7.5 h)."),
    ("Within planned window", "Within \u00b1 the time window set on page 1 of your target bedtime or wake-up time."),
    ("Daily self-assessment 1\u201310", "A subjective judgement of the day. It never replaces the recorded evidence and "
     "is not used to prove performance."),
]


def rules_page(p: PDF):
    p.new_page("Rules")
    y = page_head(p, "SETUP \u00b7 OPERATING RULES", "Marking Key, Definitions & 10-Day Plan",
                  right="READ ONCE \u00b7 PLAN BEFORE DAY 1",
                  subtitle="Every metric means the same thing on every day. When in doubt, use the definition below.")

    # ---- daily routine
    y = p.section(y, "1", "DAILY ROUTINE", "Target: 3\u20135 minutes per day in total.") + 1.2
    steps = [("MORNING \u00b7 ~1 MIN", "Section A, primary priority (D) and planned focused minutes (B)."),
             ("DURING THE DAY", "Log each work session in B when it ends: times, net minutes, distraction tally."),
             ("EVENING \u00b7 ~3 MIN", "Complete C, D, E, F and G. Prepare tomorrow's primary priority."),
             ("NEXT MORNING", "Actual bedtime (A) and habit 7 (went to bed within window).")]
    sw = CW / 4
    sh = 16.0
    for i, (head, body) in enumerate(steps):
        x = ML + i * sw
        p.rect(x, y, sw, sh, lw=0.45, g=RULE)
        p.text(x + 1.6, y + 3.3, head, F["B"], 6.8, INK, tracking=0.4)
        p.para(x + 1.6, y + 7.0, body, sw - 3.2, F["R"], 7.2, leading=3.2)
    p.rect(ML, y, CW, sh, lw=0.7, g=INK)
    y += sh + 3.0

    # ---- marking key
    y = p.section(y, "2", "MARKING KEY", "Use exactly these marks so the 10-day counts stay comparable.") + 1.2
    keys = [
        ("box", "DONE", "Completed fully, as planned or defined."),
        ("box", "PARTIAL", "Started or partly done, but not to the full plan."),
        ("box", "MISSED", "Planned and not done."),
        ("txt", "N/R", "Not recorded: missing data, left out of all counts and averages."),
        ("txt", "N/A", "Did not apply today (e.g. no work planned); left out of that count."),
        ("txt", "M / E", "Measured (device, app, timer) or Estimated (your best judgement)."),
        ("txt", "1 \u2013 5", "Circle one. 1 = very low, 5 = very high. Stress: 5 = most stressed."),
        ("box", "YES / NO", "Tick one. YES only when the stated condition is fully met."),
    ]
    kw = CW / 2
    kh = 7.0
    for i, (kind, mark, desc) in enumerate(keys):
        col, row = i % 2, i // 2
        x = ML + col * kw
        yy = y + row * kh
        p.rect(x, yy, kw, kh, lw=0.4, g=RULE)
        mx = x + 1.6
        if kind == "box":
            p.checkbox(mx, yy + kh / 2)
            p.text(mx + 4.0, yy + kh / 2 + 0.9, mark, F["B"], 7.2, INK)
        elif kind == "rate":
            p.rating(mx, yy + kh / 2, [1, 5], pitch=7.0, r=1.6, fsize=6.2)
            p.text(mx + 3.6, yy + kh / 2 + 0.9, "\u2013", F["B"], 7.2, INK)
        else:
            p.text(mx, yy + kh / 2 + 0.9, mark, F["B"], 7.4, INK)
        p.text(x + 21, yy + kh / 2 + 0.95, desc, F["R"], 7.2, INK, max_w=kw - 22.5, min_size=7.0)
    p.rect(ML, y, CW, kh * 4, lw=0.7, g=INK)
    y += kh * 4 + 3.0

    # ---- definitions
    y = p.section(y, "3", "METRIC DEFINITIONS", "Anything that could be interpreted two ways is defined here.") + 0.6
    tw = 43.0
    dsz = 7.4
    lead = 3.2
    for term, body in DEFINITIONS:
        tl = p.wrap(term, F["SB"], dsz, tw - 2.5)
        bl = p.wrap(body, F["R"], dsz, CW - tw - 2.5)
        n = max(len(tl), len(bl))
        rh = n * lead + 1.9
        yy = y + 2.85
        for ln in tl:
            p.text(ML + 1.2, yy, ln, F["SB"], dsz, INK)
            yy += lead
        yy = y + 2.85
        for ln in bl:
            p.text(ML + tw, yy, ln, F["R"], dsz, INK)
            yy += lead
        y += rh
        p.line(ML, y, PAGE_W - MR, y, w=0.3, g=FAINT)
    y += 3.0

    # ---- 10-day plan
    y = p.section(y, "4", "10-DAY PLAN \u2014 COMPLETE BEFORE DAY 1",
                  "Rest decided here in advance counts as PLANNED REST.") + 1.2
    n = CONFIG["days"]
    lw_ = 36.0
    dw = (CW - lw_) / n
    hh = 5.4
    rows = [("DATE", ""), ("PLANNED TRAINING", "RUN / OTHER / REST"), ("PLANNED RUN DISTANCE", "km"),
            ("PLANNED FOCUSED WORK", "net min"), ("KNOWN CONSTRAINTS", "exam, travel, shift\u2026")]
    rh = 8.6
    p.rect(ML, y, CW, hh, lw=0, g=RULE, fill=FILL, stroke=False)
    p.text(ML + 1.4, y + 3.75, "DAY", F["B"], 6.8, INK, tracking=0.4)
    sd = start_date()
    for d in range(n):
        p.text(ML + lw_ + dw * (d + 0.5), y + 3.85, f"{d + 1:02d}", F["B"], 7.6, INK, align="center")
    yy = y + hh
    for i, (lab, unit) in enumerate(rows):
        p.text(ML + 1.4, yy + 3.2, lab, F["SB"], 6.3, DARK, tracking=0.2, max_w=lw_ - 2.5)
        if unit:
            p.text(ML + 1.4, yy + 6.2, unit, F["R"], 6.3, MID)
        if i == 0 and sd:
            for d in range(n):
                p.text(ML + lw_ + dw * (d + 0.5), yy + 4.9, (sd + dt.timedelta(days=d)).strftime("%d/%m"),
                       F["M"], 7.6, INK, align="center")
        p.line(ML, yy + rh, PAGE_W - MR, yy + rh, w=0.4, g=RULE)
        yy += rh
    for d in range(n + 1):
        p.line(ML + lw_ + dw * d, y, ML + lw_ + dw * d, yy, w=0.4, g=RULE)
    p.rect(ML, y, CW, yy - y, lw=0.7, g=INK)
    y = yy + 1.6
    p.para(ML, y + 2.6, "Changing the plan mid-way is allowed: strike through, write the new plan and the reason, and "
           "never erase. A rest day added after the day has started is a RECOVERY CHOICE (if for health) or an "
           "UNPLANNED MISS \u2014 not a planned rest.", CW, F["I"], 7.2, leading=3.2, g=DARK)
    p.finish_page("SETUP  \u00b7  OPERATING RULES & 10-DAY PLAN")


# =============================================================================
# Generic ruled table
# =============================================================================
def table(p: PDF, x, y, cols, rows, th=7.0, rh=7.0, hsize=6.4, shade_rows=(), bold_rows=(),
          body_size=7.0, first_col_font=None, center_cols=()):
    """cols = [(header, width)] ('|' splits header lines); rows = [[cell text or ''] ...].
    rh may be a number or a list of per-row heights. Returns the y of the table bottom."""
    tw = sum(w for _, w in cols)
    p.rect(x, y, tw, th, lw=0, g=RULE, fill=FILL, stroke=False)
    cx = x
    for lab, w in cols:
        parts = lab.split("|")
        lead = 2.45
        y0 = y + th / 2 - (len(parts) - 1) * lead / 2 + 0.85
        for k, part in enumerate(parts):
            p.text(cx + w / 2, y0 + k * lead, part, F["SB"], hsize, DARK, align="center", tracking=0.1,
                   max_w=w - 1.4, min_size=6.2)
        cx += w
    yy = y + th
    for i, row in enumerate(rows):
        h = rh[i] if isinstance(rh, (list, tuple)) else rh
        if i in shade_rows:
            p.rect(x, yy, tw, h, lw=0, g=RULE, fill=FILL_SOFT, stroke=False)
        p.line(x, yy + h, x + tw, yy + h, w=0.4, g=RULE)
        cx = x
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if val:
                font = F["B"] if i in bold_rows else (first_col_font or F["SB"]) if j == 0 else F["R"]
                lines = p.wrap(val, font, body_size, w - 2.6)
                if len(lines) > 2:
                    p.warnings.append(f"p{p.page} table cell wraps >2 lines: '{val[:30]}'")
                lead = body_size * 0.3528 * 1.2
                y0 = yy + h / 2 - (len(lines) - 1) * lead / 2 + body_size * 0.3528 * 0.35
                for k, ln in enumerate(lines):
                    if j in center_cols:
                        p.text(cx + w / 2, y0 + k * lead, ln, font, body_size, INK, align="center", max_w=w - 2.0)
                    else:
                        p.text(cx + 1.3, y0 + k * lead, ln, font, body_size, INK, max_w=w - 2.6)
            cx += w
        yy += h
    cx = x
    for _, w in cols[:-1]:
        cx += w
        p.line(cx, y, cx, yy, w=0.4, g=RULE)
    p.rect(x, y, tw, yy - y, lw=0.7, g=INK)
    return yy


def note(p: PDF, y, s, size=7.2, g=DARK, x=ML, w=CW):
    """Italic note under a block. Returns y after it."""
    return p.para(x, y + 2.9, s, w, F["I"], size, leading=3.15, g=g) - 1.4


# =============================================================================
# PAGE 13 — 10-DAY TREND & SUMMARY
# =============================================================================
def summary_page(p: PDF):
    p.new_page("Summary")
    y = page_head(p, "AFTER DAY 10 \u00b7 10-DAY SUMMARY", "10-Day Trend & Summary", right="TRANSCRIBE FROM THE DAILY PAGES",
                  subtitle="Copy each value exactly as recorded. Where a daily page says N/R, write N/R here \u2014 never 0.")
    y = p.section(y, "1", "DAILY RECORD", "One row per day. Mark estimated values with E.") + 1.2
    n = CONFIG["days"]
    cols = [("DAY", 10), ("DATE", 20), ("FOCUSED|WORK|net min", 21), ("FOCUS|TARGET MET|YES / NO", 18),
            ("RUNNING|DISTANCE|km", 19), ("SLEEP|DURATION|h", 18), ("MORNING|ENERGY|1\u20135", 17),
            ("SCREEN|DISTRACTION|min (E)", 22), ("PRIMARY|PRIORITY|DONE/PART/MISS", 21), ("DAILY|SELF-RATING|1\u201310", 20)]
    sd = start_date()
    rows = [[f"{d:02d}", (sd + dt.timedelta(days=d - 1)).strftime("%d %b") if sd else ""] + [""] * 8
            for d in range(1, n + 1)]
    rows.append(["n", "days recorded"] + [""] * 8)
    yb = table(p, ML, y, cols, rows, th=10.4, rh=[7.8] * n + [7.0], shade_rows=(n,), bold_rows=(n,),
               center_cols=(0,), body_size=7.4)
    y = note(p, yb, "Screen distraction = recreational screen time from Section E (unplanned scrolling is part of it). "
             "Bottom row: write n, the number of days with a recorded value in each column.") + 2.2

    # ---- trend plot
    y = p.section(y, "2", "TREND PLOT \u2014 FOCUSED MINUTES",
                  "Bar = focused minutes. Draw your target as a line. Mark N/R days with \u00d7 (not a zero bar).") + 1.2
    ph = 34.0
    ax_w = 16.0
    gw = CW - ax_w
    p.rect(ML, y, CW, ph, lw=0.7, g=INK)
    p.text(ML + 1.3, y + 3.0, "SCALE", F["SB"], 6.4, DARK, tracking=0.3)
    p.text(ML + 1.3, y + 5.6, "(write values)", F["I"], 6.3, MID)
    gy0, gy1 = y + 7.0, y + ph - 6.0
    steps = 5
    for k in range(steps + 1):
        yy = gy0 + (gy1 - gy0) * k / steps
        p.line(ML + ax_w, yy, PAGE_W - MR - 1.5, yy, w=0.3 if k < steps else 0.6, g=FAINT if k < steps else INK)
        p.line(ML + ax_w - 5.5, yy, ML + ax_w - 1.0, yy, w=0.3, g=RULE)
    dwp = (gw - 1.5) / n
    for d in range(n):
        cx = ML + ax_w + dwp * (d + 0.5)
        p.line(ML + ax_w + dwp * (d + 1), gy0, ML + ax_w + dwp * (d + 1), gy1, w=0.25, g=FAINT, dash=[1, 1.5])
        p.text(cx, y + ph - 2.2, f"DAY {d + 1:02d}", F["SB"], 6.4, DARK, align="center", tracking=0.2)
    y += ph + 3.0

    # ---- totals with explicit formulas
    y = p.section(y, "3", "10-DAY TOTALS & AVERAGES",
                  "Use recorded values only. Every result must show its n.") + 1.2
    cols = [("MEASURE", 54), ("RESULT", 30), ("BASED ON", 20), ("CALCULATION RULE", 82)]
    rows = [
        ["Total focused-work minutes", "min", "n =", "Sum of the recorded daily totals. N/R days are left out, never counted as 0."],
        ["Total focused-work hours", "h", "n =", "Total focused minutes \u00f7 60, rounded to 0.1 h."],
        ["Average focused minutes per day", "min / day", "n =", "Total focused minutes \u00f7 n (days with a recorded total)."],
        ["Total running distance", "km", "n =", "Sum of recorded distances. A rest day recorded as 0 km counts as 0; N/R is left out."],
        ["Number of running days", "days", "of n =", "Count of days marked Running completed = YES."],
        ["Average sleep duration", "h / night", "n =", "Sum of recorded sleep hours \u00f7 n, rounded to 0.1 h."],
        ["Days primary priority completed", "DONE __ PART __", "of n =", "Count DONE as completed. Report PARTIAL separately \u2014 never merge them."],
        ["Days focused-work target achieved", "days", "of n =", "Count of YES. N/R and N/A days are left out of n."],
    ]
    # units are printed small and right-aligned inside the RESULT/BASED ON cells, so draw the table without them
    blank = [[r[0], "", "", r[3]] for r in rows]
    yb = table(p, ML, y, cols, blank, th=5.6, rh=7.4, body_size=7.0)
    for i, r in enumerate(rows):
        ry = y + 5.6 + i * 7.4
        p.text(ML + 54 + 30 - 1.3, ry + 4.9, r[1], F["R"], 6.3, MID, align="right")
        p.text(ML + 84 + 1.3, ry + 4.9, r[2], F["R"], 6.6, MID)
    y = yb + 2.2
    rules = [("Calculation rules.", F["B"]),
             ("1 \u00b7 N/R is missing data: never 0, never a success, never a failure. "
              "2 \u00b7 Write n beside every count and average, e.g. \u201c212 min/day (n = 8)\u201d. "
              "3 \u00b7 A genuine 0 is data \u2014 include it. "
              "4 \u00b7 Round only at the end and never beyond what was recorded (whole minutes; 0.1 h; 0.1 km). "
              "5 \u00b7 If most values behind a figure are estimates (E), label the figure \u201cestimated\u201d.", F["R"])]
    bh = 13.6
    p.rect(ML, y, CW, bh, lw=0.7, g=INK, fill=FILL_SOFT)
    p.rich_para(ML + 2.0, y + 3.9, [(t, f, INK) for t, f in rules], CW - 4.0, size=7.3, leading=3.25)
    p.finish_page("AFTER DAY 10  \u00b7  10-DAY TREND & SUMMARY")


# =============================================================================
# PAGE 14 — A. CONSISTENCY ANALYSIS
# =============================================================================
def analysis_a(p: PDF):
    p.new_page("Analysis A")
    y = page_head(p, "FINAL ANALYSIS \u00b7 A", "Consistency Analysis", right="COMPLETE AFTER DAY 10",
                  subtitle="Base every answer on recorded entries. Count behaviour and frequency \u2014 do not judge character.")
    y = p.section(y, "1", "HABIT TALLY \u2014 FROM SECTION D OF EACH DAY",
                  "Count each mark across the 10 pages. The primary priority is scored separately.") + 1.2
    cols = [("#", 8), ("BEHAVIOUR", 80), ("DONE", 14), ("PARTIAL", 14), ("MISSED", 14), ("N/R \u00b7 N/A", 16),
            ("RECORDED|n = D + P + M", 18), ("COMPLETION|DONE of n", 22)]
    rows = [["P", "Completed my primary priority"] + [""] * 6]
    rows += [[str(i + 1), h.rstrip(".")] + [""] * 6 for i, h in enumerate(CONFIG["habits"])]
    yb = table(p, ML, y, cols, rows, th=7.4, rh=[7.6] + [6.6] * len(CONFIG["habits"]), bold_rows=(0,),
               center_cols=(0,), body_size=7.0)
    p.rect(ML, y + 7.4, CW, 7.6, lw=1.1, g=INK)
    y = note(p, yb, "Completion is written as a count, e.g. \u201c6 of 9\u201d, not a percentage \u2014 ten days are too few "
             "for precise rates. N/R and N/A are excluded from n.") + 2.4

    y = p.section(y, "2", "KEY COUNTS", "Copy from the 10-day summary.") + 1.2
    h = 13.0
    w3 = CW / 3
    p.cell(ML, y, w3, h, "DAYS I ACHIEVED MY FOCUS TARGET", unit="days, of n = ____")
    p.cell(ML + w3, y, w3, h, "DAYS I COMPLETED MY PRIMARY PRIORITY", unit="DONE ____ PARTIAL ____ of n = ____")
    p.cell(ML + 2 * w3, y, w3, h, "LONGEST STREAK OF MEETING MY FOCUS TARGET", unit="consecutive days \u00b7 Days ___ to ___")
    p.rect(ML, y, CW, h, lw=0.7, g=INK)
    y = note(p, y + h, "Streak = consecutive days marked YES. An N/R day ends a verified streak \u2014 note it, "
             "e.g. \u201c4 days (N/R on Day 6)\u201d.") + 2.4

    y = p.section(y, "3", "FIRST HALF VS SECOND HALF", "Shows direction of change. Report n for each average.") + 1.2
    cols = [("PERIOD", 30), ("AVG FOCUSED|min / day (n)", 28), ("FOCUS TARGET|days met (of n)", 26),
            ("PRIORITY|DONE (of n)", 25), ("AVG SLEEP|h (n)", 24), ("RUNNING|days", 22), ("AVG SELF-RATING|1\u201310 (n)", 31)]
    rows = [["Days 01\u201305"] + [""] * 6, ["Days 06\u201310"] + [""] * 6, ["Change (2nd \u2212 1st)"] + [""] * 6]
    y = table(p, ML, y, cols, rows, th=7.4, rh=7.4, shade_rows=(2,), body_size=7.0) + 3.0

    y = p.section(y, "4", "FINDINGS",
                  "Best / worst day: judge by primary priority status first, then focused minutes against plan.") + 1.2
    h = 25.0
    hw = CW / 2
    cells = [("BEST DAY \u2014 DAY ___ \u00b7 EVIDENCE", "WORST-PERFORMING DAY \u2014 DAY ___ \u00b7 EVIDENCE"),
             ("MOST CONSISTENT BEHAVIOUR (HIGHEST DONE COUNT)", "MOST FREQUENTLY MISSED HABIT (HIGHEST MISSED COUNT)"),
             ("BIGGEST IMPROVEMENT DURING THE 10 DAYS", "BIGGEST RECURRING WEAKNESS (SEEN ON 3 OR MORE DAYS)")]
    for left, right in cells:
        text_cell(p, ML, y, hw, h, left, lines=2)
        text_cell(p, ML + hw, y, hw, h, right, lines=2)
        y += h
    p.rect(ML, y - 3 * h, CW, 3 * h, lw=0.7, g=INK)
    p.finish_page("FINAL ANALYSIS  \u00b7  A. CONSISTENCY")


# =============================================================================
# PAGE 15 — B. TIME AND PRODUCTIVITY ANALYSIS
# =============================================================================
def analysis_b(p: PDF):
    p.new_page("Analysis B")
    y = page_head(p, "FINAL ANALYSIS \u00b7 B", "Time & Productivity Analysis", right="COMPLETE AFTER DAY 10",
                  subtitle="Ten days of data reveal patterns worth testing \u2014 not proof of what caused them.")
    y = p.section(y, "1", "INTENTION VS REALITY",
                  "Compare only days on which both planned and actual minutes were recorded.") + 1.2
    h = 12.0
    w4 = CW / 4
    p.cell(ML, y, w4, h, "PLANNED FOCUSED MINUTES, TOTAL", unit="min \u00b7 n = ____")
    p.cell(ML + w4, y, w4, h, "ACTUAL FOCUSED MINUTES, TOTAL", unit="min \u00b7 n = ____")
    p.cell(ML + 2 * w4, y, w4, h, "DIFFERENCE (ACTUAL \u2212 PLANNED)", unit="min")
    p.cell(ML + 3 * w4, y, w4, h, "DAYS ACTUAL \u2265 PLANNED", unit="of n = ____")
    y += h
    text_cell(p, ML, y, CW, 17.0, "1 \u00b7 DID MY ACTUAL FOCUSED TIME MATCH MY INTENTIONS? WHAT DOES THE GAP SHOW?", lines=2)
    p.rect(ML, y - h, CW, h + 17.0, lw=0.7, g=INK)
    y += 17.0 + 3.0

    y = p.section(y, "2", "BEST VS WORST DAYS \u2014 MANUAL COMPARISON",
                  "Observations, not causes: three days against three cannot prove anything.") + 1.2
    cols = [("GROUP", 26), ("DAY #", 14), ("FOCUSED|TIME min", 22), ("SLEEP|h", 19), ("ENERGY|1\u20135", 19),
            ("DISTRACTIONS|screen min", 25), ("EXERCISE|km / min / rest", 29), ("PRIMARY TASK|DONE / PART / MISS", 32)]
    rows = [["Best day 1"] + [""] * 7, ["Best day 2"] + [""] * 7, ["Best day 3"] + [""] * 7,
            ["Best \u2014 average"] + [""] * 7,
            ["Worst day 1"] + [""] * 7, ["Worst day 2"] + [""] * 7, ["Worst day 3"] + [""] * 7,
            ["Worst \u2014 average"] + [""] * 7]
    yb = table(p, ML, y, cols, rows, th=7.6, rh=7.0, shade_rows=(3, 7), bold_rows=(3, 7), body_size=7.0)
    p.line(ML, y + 7.6 + 4 * 7.0, PAGE_W - MR, y + 7.6 + 4 * 7.0, w=1.0, g=INK)
    y = yb
    text_cell(p, ML, y, CW, 9.0, "HOW I RANKED BEST AND WORST DAYS (CRITERIA USED)")
    y += 9.0
    text_cell(p, ML, y, CW, 15.0, "WHAT DIFFERS MOST BETWEEN THE TWO GROUPS? (AN OBSERVATION TO TEST, NOT A CAUSE)", lines=2)
    p.rect(ML, y - 9.0, CW, 24.0, lw=0.7, g=INK)
    y += 15.0 + 3.0

    y = p.section(y, "3", "INVESTIGATION", "Answer from the record. Write the days or counts that support each answer.") + 1.2
    y3 = y
    text_cell(p, ML, y, CW, 18.0, "2 \u00b7 WHICH DAYS GENERATED THE MOST MEANINGFUL WORK? (DAYS \u00b7 TASKS THAT MATERIALLY ADVANCED MY GOALS)", lines=2)
    y += 18.0
    h = 23.0
    p.cell(ML, y, CW, h, "3 \u00b7 WAS PRODUCTIVITY AFFECTED BY SLEEP, DISTRACTIONS, WORKLOAD OR OTHER FACTORS? "
           "TICK WHAT APPEARED ALONGSIDE WEAKER DAYS:")
    p.options(ML + 1.5, y + 6.6, ["SHORT SLEEP", "HIGH DISTRACTION", "HEAVY WORKLOAD", "LOW ENERGY / MOOD",
                                   "NO EXERCISE", "ILLNESS / PAIN", "OTHER: ____________"], gap=5.0)
    p.text(ML + 1.5, y + 11.4, "What I observed (association only):", F["I"], 6.6, MID)
    guide_lines(p, ML, y + 9.0, CW, h - 9.0, 2, top_pad=1.0)
    y += h
    text_cell(p, ML, y, CW, 18.0, "4 \u00b7 WHICH ACTIVITIES REPEATEDLY CONSUMED TIME WITHOUT PRODUCING USEFUL OUTCOMES? "
              "(ACTIVITY \u00b7 DAYS SEEN \u00b7 APPROX. MIN)", lines=2)
    y += 18.0
    h = 20.0
    p.cell(ML, y, CW, h, "5 \u00b7 WAS I CONFUSING BEING BUSY WITH MAKING PROGRESS?")
    p.options(ML + 1.5, y + 6.6, ["YES", "PARTLY", "NO"], gap=5.0)
    p.text(ML + 50, y + 7.4, "Evidence: focused hours ______  vs  days with a task that materially advanced my goals ______ of n = ____",
           F["R"], 7.0, DARK)
    guide_lines(p, ML, y + 8.0, CW, h - 8.0, 2, top_pad=1.5)
    y += h
    p.rect(ML, y3, CW, y - y3, lw=0.7, g=INK)
    p.finish_page("FINAL ANALYSIS  \u00b7  B. TIME & PRODUCTIVITY")


# =============================================================================
# PAGE 16 — C. PHYSICAL PERFORMANCE ANALYSIS
# =============================================================================
def analysis_c(p: PDF):
    p.new_page("Analysis C")
    y = page_head(p, "FINAL ANALYSIS \u00b7 C", "Physical Performance Analysis", right="COMPLETE AFTER DAY 10",
                  subtitle="Training load is judged against recovery and symptoms. More distance is not automatically better.")
    y = p.section(y, "1", "10-DAY TRAINING STRIP \u2014 FROM SECTION C",
                  "REST = planned rest \u00b7 REC = recovery choice \u00b7 MISS = unplanned miss") + 1.2
    n = CONFIG["days"]
    lw_ = 42.0
    dw = (CW - lw_) / n
    labels = [("PLANNED (10-DAY PLAN)", "RUN / OTHER / REST"), ("ACTUAL", "RUN / OTHER / REST / REC / MISS"),
              ("RUNNING DISTANCE", "km"), ("RUNNING DURATION", "min"), ("PERCEIVED EFFORT", "RPE 1\u201310"),
              ("MOBILITY / STRETCHING", "YES / NO"), ("FATIGUE, PAIN OR DISCOMFORT", "YES / NO"),
              ("SLEEP DURATION", "h")]
    cols = [("", lw_)] + [(f"DAY {d + 1:02d}", dw) for d in range(n)]
    yb = table(p, ML, y, cols, [[""] * (n + 1) for _ in labels], th=5.8, rh=7.8, body_size=7.0)
    for i, (lab, unit) in enumerate(labels):
        ry = y + 5.8 + i * 7.8
        ry += 0.2
        p.text(ML + 1.4, ry + 3.1, lab, F["SB"], 6.3, DARK, tracking=0.15, max_w=lw_ - 2.6)
        p.text(ML + 1.4, ry + 6.1, unit, F["R"], 6.3, MID, max_w=lw_ - 2.6)
    y = yb + 3.0

    y = p.section(y, "2", "TOTALS", "Recorded values only \u2014 write n where asked.") + 1.2
    h = 13.0
    items = [("TOTAL RUNNING VOLUME", "km \u00b7 n = ___"), ("NUMBER OF RUNNING DAYS", "days"),
             ("PLANNED REST DAYS TAKEN", "days"), ("RECOVERY CHOICES", "days"), ("UNPLANNED MISSES", "days"),
             ("DAYS WITH FATIGUE / PAIN", "days")]
    w6 = CW / len(items)
    for i, (lab, unit) in enumerate(items):
        p.cell(ML + i * w6, y, w6, h, lab, unit=unit)
    p.rect(ML, y, CW, h, lw=0.7, g=INK)
    y += h + 3.0

    y = p.section(y, "3", "OBSERVATIONS", "Compare effort at similar distance or pace before calling a trend.") + 1.2
    h = 16.5
    p.cell(ML, y, CW, h, "PERCEIVED EXERTION TREND")
    p.options(ML + 1.5, y + 6.7, ["RISING", "STABLE", "FALLING", "TOO LITTLE DATA"], gap=6.0)
    p.text(ML + 96, y + 7.4, "Evidence:", F["I"], 6.6, MID)
    guide_lines(p, ML, y + 7.5, CW, h - 7.5, 1, top_pad=1.0)
    y += h
    text_cell(p, ML, y, CW, h, "RECOVERY CONSISTENCY \u2014 PLANNED REST TAKEN AS PLANNED? MOBILITY ON ___ OF n = ___ DAYS", lines=1)
    y += h
    text_cell(p, ML, y, CW, h, "SLEEP AND FATIGUE OBSERVATIONS", lines=1)
    y += h
    h2 = 24.0
    text_cell(p, ML, y, CW / 2, h2, "WHAT I SHOULD CONTINUE", lines=2)
    text_cell(p, ML + CW / 2, y, CW / 2, h2, "WHAT I SHOULD ADJUST", lines=2)
    y += h2
    p.rect(ML, y - 3 * h - h2, CW, 3 * h + h2, lw=0.7, g=INK)
    y += 3.0

    y = p.section(y, "4", "NEXT TRAINING BLOCK \u2014 DECISION GATE",
                  "The next plan follows recovery, symptoms and tolerance \u2014 not ambition.") + 1.2
    gh = 33.0
    p.rect(ML, y, CW, gh, lw=0.7, g=INK)
    p.text(ML + 2.0, y + 4.2, "Consider any increase in running volume only if every statement below is true:",
           F["SB"], 7.4, INK)
    checks = ["No pain, injury or illness flags during the 10 days.",
              "Perceived effort was stable or falling at a similar distance or pace.",
              "Sleep was adequate on most recorded nights.",
              "Planned rest days were actually taken.",
              "I finished most sessions feeling I could have done a little more."]
    cy = y + 8.6
    for i, chk in enumerate(checks):
        col, row = i % 2, i // 2
        cx = ML + 2.0 + col * (CW / 2)
        p.checkbox(cx, cy + row * 5.4 - 1.0)
        p.text(cx + 4.2, cy + row * 5.4, chk, F["R"], 7.2, INK)
    dy = y + 26.0
    p.text(ML + 2.0, dy, "DECISION FOR THE NEXT 10 DAYS:", F["B"], 7.0, INK, tracking=0.3)
    p.options(ML + 46.0, dy - 1.0, ["REDUCE", "MAINTAIN", "INCREASE MODESTLY"], gap=6.0)
    p.text(ML + 2.0, y + gh - 2.2,
           "Sharp or persistent pain, chest pain, dizziness, illness or unusual fatigue: stop training and seek qualified medical advice.",
           F["I"], 6.8, DARK)
    p.finish_page("FINAL ANALYSIS  \u00b7  C. PHYSICAL PERFORMANCE")


# =============================================================================
# PAGE 17 — D. PERSONAL PATTERN DETECTION
# =============================================================================
def analysis_d(p: PDF):
    p.new_page("Analysis D")
    y = page_head(p, "FINAL ANALYSIS \u00b7 D", "Personal Pattern Detection", right="COMPLETE AFTER DAY 10",
                  subtitle="Describe what the record shows: behaviour, frequency and context.")
    bh = 13.0
    p.rect(ML, y, CW, bh, lw=1.1, g=INK, fill=FILL_SOFT)
    p.rich_para(ML + 2.5, y + 4.4, [
        ("Write findings as evidence, not labels.", F["B"], INK),
        ("\u201cOn 4 of 9 recorded days I started work after 10:00\u201d \u2014 not \u201cI am lazy\u201d. Isolated failures "
         "say nothing about character. Something seen on one or two days is a note; a pattern needs repetition.",
         F["R"], INK)], CW - 5, size=7.8, leading=3.6)
    y += bh + 3.0
    y = p.section(y, "1", "PATTERNS", "Right-hand column: the days or count that support each answer.") + 1.2
    ew = 42.0
    qw = CW - ew
    items = [
        ("My three most productive conditions (time, place, state, preparation)", 3),
        ("My three biggest recurring distractions", 3),
        ("The behaviour that creates the most damage to my schedule", 1),
        ("The excuse I use most often", 1),
        ("The difference between what I planned and what I repeatedly did", 2),
        ("One environmental change that would make good behaviour easier", 1),
        ("One unnecessary activity I should reduce", 1),
        ("One productive behaviour I should make easier to repeat", 1),
    ]
    # header
    p.rect(ML, y, CW, 5.4, lw=0, g=RULE, fill=FILL, stroke=False)
    p.text(ML + 1.4, y + 3.7, "QUESTION \u00b7 ANSWER", F["SB"], 6.2, DARK, tracking=0.3)
    p.text(ML + qw + ew / 2, y + 3.7, "EVIDENCE \u2014 DAYS / COUNT", F["SB"], 6.2, DARK, align="center", tracking=0.3)
    top = y
    y += 5.4
    for i, (q, n_lines) in enumerate(items):
        if n_lines == 3:
            h = 31.0
        elif n_lines == 2:
            h = 24.0
        else:
            h = 21.0
        p.line(ML, y + h, PAGE_W - MR, y + h, w=0.45, g=RULE)
        p.text(ML + 1.4, y + 3.6, f"{i + 1}", F["B"], 7.6, INK)
        p.text(ML + 5.4, y + 3.6, q, F["SB"], 7.4, INK, max_w=qw - 7)
        if n_lines == 3:
            for k in range(3):
                ly = y + 6.0 + (k + 1) * 7.8
                p.text(ML + 5.4, ly - 0.8, f"{k + 1}.", F["M"], 7.0, MID)
                p.line(ML + 9.5, ly, ML + qw - 2.0, ly, w=0.3, g=FAINT)
                p.line(ML + qw + 2.0, ly, PAGE_W - MR - 2.0, ly, w=0.3, g=FAINT)
        elif n_lines == 2:
            for k, lab in enumerate(["Planned:", "Repeatedly did:"]):
                ly = y + 6.0 + (k + 1) * 7.8
                p.text(ML + 5.4, ly - 0.8, lab, F["I"], 6.8, MID)
                p.line(ML + 25.0, ly, ML + qw - 2.0, ly, w=0.3, g=FAINT)
            p.line(ML + qw + 2.0, y + 13.8, PAGE_W - MR - 2.0, y + 13.8, w=0.3, g=FAINT)
            p.line(ML + qw + 2.0, y + 21.6, PAGE_W - MR - 2.0, y + 21.6, w=0.3, g=FAINT)
        else:
            for ly in (y + h - 10.2, y + h - 2.6):
                p.line(ML + 5.4, ly, ML + qw - 2.0, ly, w=0.3, g=FAINT)
                p.line(ML + qw + 2.0, ly, PAGE_W - MR - 2.0, ly, w=0.3, g=FAINT)
        y += h
    p.line(ML + qw, top, ML + qw, y, w=0.45, g=RULE)
    p.rect(ML, top, CW, y - top, lw=0.7, g=INK)
    p.finish_page("FINAL ANALYSIS  \u00b7  D. PERSONAL PATTERN DETECTION")


# =============================================================================
# PAGE 18 — E. THE NEXT 10-DAY ACTION PLAN
# =============================================================================
def analysis_e(p: PDF):
    p.new_page("Analysis E")
    y = page_head(p, "FINAL ANALYSIS \u00b7 E", "The Next 10-Day Action Plan", right="COMPLETE AFTER DAY 10",
                  subtitle="Few, measurable commitments beat many vague ones. Every line must be checkable on a daily page.")
    y = p.section(y, "1", "COMMITMENTS", "Fill every column. If you cannot say how you will verify it, rewrite it.") + 1.2
    y = note(p, y - 1.0, "Example \u2014 Action: two 50-minute study blocks before noon \u00b7 Measure: net focused minutes \u00b7 "
             "Target: \u2265 100 min on 8 of 10 days \u00b7 When: 08:00\u201312:00 \u00b7 Verify: Section B totals.", size=7.0) + 1.6
    cols = [("COMMITMENT", 38), ("ACTION", 44), ("MEASURE", 27), ("TARGET", 25), ("WHEN", 22),
            ("HOW I WILL|VERIFY IT", 30)]
    rows = [["Priority 1"], ["Priority 2"], ["Priority 3"], ["Focused-work target (measurable)"],
            ["Physical-training commitment (realistic)"], ["Sleep or recovery improvement"],
            ["Distraction-reduction rule"], ["Habit to stop"], ["Habit to strengthen"],
            ["Fallback plan for difficult days"]]
    rows = [r + [""] * 5 for r in rows]
    y = table(p, ML, y, cols, rows, th=7.4, rh=13.6, body_size=7.2) + 3.0

    y = p.section(y, "2", "FALLBACK & KEY MEASUREMENT", "A bad day still has a minimum standard.") + 1.2
    h = 16.5
    text_cell(p, ML, y, CW / 2, h, "A DIFFICULT DAY MEANS (TRIGGER)", lines=1)
    p.cell(ML + CW / 2, y, CW / 2, h, "MINIMUM I WILL STILL DO ON A DIFFICULT DAY")
    mx = ML + CW / 2 + 1.5
    p.text(mx, y + 8.6, "Focused work ______ min   \u00b7   Movement or rest ____________   \u00b7   In bed by ______",
           F["R"], 7.2, DARK)
    y += h
    p.cell(ML, y, 96, h, "THE SINGLE MOST IMPORTANT MEASUREMENT I WILL TRACK")
    p.cell(ML + 96, y, 40, h, "TARGET")
    p.cell(ML + 136, y, CW - 136, h, "RECORDED DAILY IN SECTION")
    p.rect(ML, y - h, CW, 2 * h, lw=0.7, g=INK)
    y += h + 4.0

    dh = 31.0
    p.rect(ML, y, CW, dh, lw=1.6, g=INK, fill=FILL_SOFT)
    p.text(ML + 4.0, y + 5.0, "DECLARATION", F["B"], 7.4, INK, tracking=1.4)
    p.text(ML + CW / 2, y + 12.6,
           "\u201cI will judge the next 10 days by what I consistently do, not by what I promise myself.\u201d",
           F["B"], 11.6, INK, align="center", max_w=CW - 8)
    p.cell(ML + 4.0, y + 16.5, 56, 11.0, "DATE", g=INK)
    p.cell(ML + 64.0, y + 16.5, CW - 68.0, 11.0, "SIGNATURE", g=INK)
    p.finish_page("FINAL ANALYSIS  \u00b7  E. NEXT 10-DAY ACTION PLAN")


# =============================================================================
# Build
# =============================================================================
def build(out_path: str, only_daily: bool = False):
    pages = [mission_page, rules_page]
    pages += [lambda p, d=d: daily_page(p, d) for d in range(1, CONFIG["days"] + 1)]
    pages += [summary_page, analysis_a, analysis_b, analysis_c, analysis_d, analysis_e]
    p = PDF(out_path, total_pages=len(pages))
    for fn in pages:
        fn(p)
    p.save()
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, CONFIG["output"]))
    args = ap.parse_args(argv)
    p = build(args.out)
    print(f"Wrote {args.out} ({p.page} pages)")
    if p.warnings:
        print("LAYOUT WARNINGS:")
        for w in p.warnings:
            print("  -", w)
        return 1
    print("Layout check: no overflow warnings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
