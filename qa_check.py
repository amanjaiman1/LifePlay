#!/usr/bin/env python3
"""
Automated quality checks for 10_Day_Personal_Performance_Audit.pdf.

    python qa_check.py [path/to/pdf] [--render out_dir]

Checks: page count and A4 size, everything inside the printable margins, content
above the footer, minimum font size, every daily sheet present with its own date
field and sections A-G, and all required phrases/sections in the document.
Requires: pymupdf (pip install pymupdf).
"""
import os
import sys

import pymupdf

MM = 72 / 25.4
A4 = (595.28, 841.89)
MARGIN_X = 12.0 * MM - 0.6        # nothing may start left of the 12 mm margin
MAX_X = (210 - 12.0) * MM + 0.6
MIN_Y = 10.0 * MM - 0.6
CONTENT_BOTTOM = 284.0 * MM + 0.6  # body content must end above the footer zone
FOOTER_BOTTOM = 292.0 * MM         # footer text must stay >= 5 mm from the paper edge
MIN_FONT = 6.2                     # pt

DAILY_SECTIONS = ["DAILY IDENTIFICATION", "FOCUSED WORK & STUDY", "PHYSICAL TRAINING & RUNNING",
                  "DAILY DISCIPLINE & HABITS", "TIME & DIGITAL DISTRACTION AUDIT", "ENERGY, MOOD & RECOVERY",
                  "DAILY SELF-REVIEW"]
DAILY_FIELDS = ["DATE", "DAY OF THE WEEK", "PREVIOUS NIGHT'S SLEEP DURATION", "ACTUAL WAKE-UP TIME",
                "PLANNED BEDTIME", "ACTUAL BEDTIME", "SUBJECT / TASK", "TOTAL FOCUSED", "PLANNED FOCUSED",
                "FOCUS TARGET ACHIEVED", "MOST PRODUCTIVE", "MAIN DISTRACTION",
                "ONE TASK COMPLETED THAT MATERIALLY ADVANCED MY GOALS", "RUNNING COMPLETED?", "RUNNING DISTANCE",
                "RUNNING DURATION", "AVERAGE PACE", "PERCEIVED EFFORT", "OTHER PHYSICAL ACTIVITY",
                "MOBILITY / STRETCHING?", "UNUSUAL FATIGUE, PAIN OR DISCOMFORT", "REST OR RECOVERY DAY?",
                "PLANNED REST", "UNPLANNED MISS", "PRIMARY PRIORITY", "DONE", "PARTIAL", "MISSED",
                "RECREATIONAL SCREEN TIME", "UNPLANNED SCROLLING", "SIGNIFICANT INTERRUPTIONS",
                "TIME LOST TO AVOIDABLE ACTIVITIES", "BIGGEST SOURCE OF WASTED TIME",
                "ONE SPECIFIC ACTION TO REDUCE THIS WASTE TOMORROW", "MORNING ENERGY", "CONCENTRATION QUALITY",
                "MOOD", "PHYSICAL FRESHNESS", "STRESS LEVEL", "SLEEP DURATION", "SLEEP QUALITY", "WATER",
                "MEALS REASONABLY CONSISTENT WITH MY NEEDS?", "ANY FACTOR AFFECTING TODAY'S PERFORMANCE",
                "DAILY SELF-ASSESSMENT", "WAS THIS SCORE BASED ON EVIDENCE?", "ONE SENTENCE EXPLAINING THE SCORE",
                "SIGNATURE / PERSONAL ACCOUNTABILITY MARK"]
DOC_PHRASES = [
    "10-DAY PERFORMANCE AUDIT",
    "Personal Discipline, Deep Work, Physical Training & Recovery",
    "Record reality, not intention.",
    "Do not manipulate the numbers to make yourself look disciplined.",
    "An honest failure is more useful than a false success.",
    "N/R is neither a success nor a failure",
    "NAME OR CALLSIGN", "START DATE", "END DATE", "PRIMARY OBJECTIVE FOR THESE 10 DAYS",
    "MOST IMPORTANT AREA I WANT TO IMPROVE", "DAILY FOCUSED-WORK TARGET", "RUNNING TARGET", "TARGET BEDTIME",
    "TARGET WAKE-UP TIME", "ONE BEHAVIOUR I MUST ELIMINATE", "ONE BEHAVIOUR I MUST STRENGTHEN",
    "10-Day Trend & Summary", "Total focused-work minutes", "Total focused-work hours",
    "Average focused minutes per day", "Total running distance", "Number of running days",
    "Average sleep duration", "Days primary priority completed", "Days focused-work target achieved",
    "never counted as 0",
    "Consistency Analysis", "Time & Productivity Analysis", "Physical Performance Analysis",
    "Personal Pattern Detection", "The Next 10-Day Action Plan",
    "ACTION", "MEASURE", "TARGET", "WHEN", "VERIFY IT",
    "I will judge the next 10 days by what I consistently do, not by what I promise myself.",
]


def main():
    args = sys.argv[1:]
    render_dir = None
    if "--render" in args:
        i = args.index("--render")
        render_dir = args[i + 1]
        del args[i:i + 2]
    path = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "10_Day_Personal_Performance_Audit.pdf")
    doc = pymupdf.open(path)
    problems, info = [], []
    if doc.page_count != 18:
        problems.append(f"expected 18 pages, found {doc.page_count}")
    all_text = ""
    min_font = 99.0
    for pno, page in enumerate(doc, start=1):
        w, h = page.rect.width, page.rect.height
        if abs(w - A4[0]) > 1 or abs(h - A4[1]) > 1:
            problems.append(f"p{pno}: page size {w:.1f}x{h:.1f} pt is not A4 portrait")
        text = page.get_text()
        all_text += text + "\n"
        body_bottom = 0.0
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    x0, y0, x1, y1 = span["bbox"]
                    min_font = min(min_font, span["size"])
                    if span["size"] < MIN_FONT - 0.01:
                        problems.append(f"p{pno}: font {span['size']:.2f}pt < {MIN_FONT}pt: {span['text'][:30]!r}")
                    if x0 < MARGIN_X or x1 > MAX_X or y0 < MIN_Y or y1 > FOOTER_BOTTOM:
                        problems.append(f"p{pno}: text outside margins {span['text'][:30]!r} bbox={tuple(round(v / MM, 1) for v in span['bbox'])}")
                    if y0 < 286.5 * MM:
                        body_bottom = max(body_bottom, y1)
        for d in page.get_drawings():
            r = d["rect"]
            if r.x0 < MARGIN_X - 1 or r.x1 > MAX_X + 1 or r.y0 < MIN_Y - 1:
                problems.append(f"p{pno}: drawing outside margins {tuple(round(v / MM, 1) for v in r)}")
            if r.y1 < 286.5 * MM:
                body_bottom = max(body_bottom, r.y1)
        if body_bottom > CONTENT_BOTTOM:
            problems.append(f"p{pno}: body content reaches {body_bottom / MM:.1f} mm (limit 284 mm)")
        if f"PAGE {pno} OF {doc.page_count}" not in text:
            problems.append(f"p{pno}: page number missing")
        info.append(f"p{pno:02d}: body ends at {body_bottom / MM:5.1f} mm  (spare {284 - body_bottom / MM:4.1f} mm)")
        # daily sheets are pages 3-12
        if 3 <= pno <= 12:
            day = pno - 2
            if f"{day:02d}" not in text or f"DAY {day:02d} OF 10" not in text:
                problems.append(f"p{pno}: day label for Day {day:02d} missing")
            for s in DAILY_SECTIONS:
                if s not in text:
                    problems.append(f"p{pno}: section missing: {s}")
            for fld in DAILY_FIELDS:
                if fld not in text:
                    problems.append(f"p{pno}: field missing: {fld}")
            for wd in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]:
                if wd not in text:
                    problems.append(f"p{pno}: weekday {wd} missing")
        if render_dir:
            os.makedirs(render_dir, exist_ok=True)
            page.get_pixmap(dpi=110).save(os.path.join(render_dir, f"page_{pno:02d}.png"))
    flat = " ".join(all_text.split())
    for phrase in DOC_PHRASES:
        if " ".join(phrase.split()) not in flat:
            problems.append(f"document phrase missing: {phrase!r}")

    print(f"File: {path}")
    print(f"Pages: {doc.page_count}  |  smallest font: {min_font:.2f} pt")
    for line in info:
        print("  " + line)
    if problems:
        print(f"\nFAILED — {len(problems)} problem(s):")
        for pr in problems:
            print("  - " + pr)
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
