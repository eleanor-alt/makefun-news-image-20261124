"""Front page for Tuesday 24 November 2026: one 1024x1024 PNG, drawn from scratch.

Standard library only. A bytearray canvas, a 5x7 bitmap font written out as
rows of "1"/"0" strings, and a hand-rolled PNG encoder. No network, no clock,
no randomness, so every run writes identical bytes.
"""

import struct
import zlib

SIZE = 1024

# --- 5x7 bitmap font: seven strings per glyph, "1" = ink, "0" = blank -------
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "01010", "00100", "00100", "00100", "01010", "10001"),
    "Y": ("10001", "01010", "00100", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11000", "11001", "00010", "00100", "01000", "10011", "00011"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
}

NAVY = (16, 38, 64)
PAPER = (247, 245, 239)
INK = (22, 26, 32)
BAND_TEXT = (238, 242, 246)
RED = (176, 32, 48)
TAG_RED = (150, 28, 44)
RULE = (198, 192, 178)
SKY = (172, 198, 218)
WHITE = (244, 244, 240)
STEP = (214, 210, 200)


class Page:
    """A flat RGB canvas with rectangle and bitmap-text drawing."""

    def __init__(self):
        self.buf = bytearray(PAPER * (SIZE * SIZE))

    def fill(self, x, y, w, h, colour):
        r, g, b = colour
        row = bytes((r, g, b)) * w
        for yy in range(y, y + h):
            start = (yy * SIZE + x) * 3
            self.buf[start:start + w * 3] = row

    def glyph_width(self, text, scale):
        return len(text) * 6 * scale - scale

    def put_text(self, x, y, text, scale, colour):
        cursor = x
        for ch in text.upper():
            rows = GLYPHS.get(ch, GLYPHS[" "])
            for row_i, row in enumerate(rows):
                for col_i, bit in enumerate(row):
                    if bit == "1":
                        self.fill(cursor + col_i * scale, y + row_i * scale,
                                  scale, scale, colour)
            cursor += 6 * scale
        return cursor - x

    def wrap_text(self, text, scale, width):
        lines = []
        current = ""
        for word in text.split():
            trial = (current + " " + word).strip()
            if self.glyph_width(trial, scale) <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines


# --- the day's stories: lead + eight, all reported on 24 November 2026 -----
LEAD_HEADLINE = "DEMOCRATS CLINCH 259 HOUSE SEATS - LARGEST MAJORITY SINCE 1990"
LEAD_SUB = "DEMOCRATS TAKE BOTH CHAMBERS AS THE FINAL RACES ARE CALLED"

GRID = [
    ("MIDDLE EAST", "HOUTHI STRIKE HITS RIYADH'S PIF TOWER; 11 PEOPLE HURT"),
    ("GAZA", "ISRAELI STRIKE KILLS HAMAS SECURITY CHIEF ABU NAHEL IN GAZA"),
    ("UKRAINE WAR", "RUSSIAN STRIKE ON ZAPORIZHZHIA KILLS 2, WOUNDS 48"),
    ("EAST ASIA", "RUSSIAN JETS ENTER SOUTH KOREA'S AIR ZONE; SEOUL SCRAMBLES FIGHTERS"),
    ("SPACE", "CHINA LAUNCHES SHENZHOU-24 WITH FIRST PAKISTANI ASTRONAUT ABOARD"),
    ("FRANCE", "SARKOZY CORRUPTION CASE ORDERED TO TRIAL IN FRANCE"),
    ("COLOMBIA", "CAR BOMB IN VILLAVICENCIO, COLOMBIA, INJURES AT LEAST 23"),
    ("UNITED STATES", "TRUMP AWARDS MEDAL OF FREEDOM TO RUDY GIULIANI"),
]


def draw_capitol(page, x, y, w, h):
    """A simple geometric US Capitol dome, drawn with rectangles only."""
    page.fill(x, y, w, h, SKY)
    cx = x + w // 2
    # Flag on the lantern.
    page.fill(cx - 1, y + 42, 2, 18, INK)
    page.fill(cx + 1, y + 42, 18, 9, RED)
    # Lantern and dome tiers, widest at the bottom, in finer steps so the
    # curve reads as a dome rather than a staircase.
    page.fill(cx - 6, y + 60, 12, 10, WHITE)
    for i, half in enumerate((12, 22, 32, 40, 47, 53, 57, 60)):
        page.fill(cx - half, y + 70 + i * 8, half * 2, 8, WHITE)
    # Drum and colonnade.
    page.fill(cx - 60, y + 134, 120, 12, WHITE)
    for i in range(5):
        col_x = cx - 52 + i * 26
        page.fill(col_x, y + 146, 10, 40, WHITE)
    # Base and steps.
    page.fill(cx - 68, y + 186, 136, 12, WHITE)
    page.fill(cx - 80, y + 198, 160, 8, STEP)
    page.fill(cx - 92, y + 206, 184, 8, STEP)
    page.fill(x, y + h - 30, w, 30, (148, 176, 196))
    page.put_text(x + 14, y + h - 24, "WASHINGTON", 2, NAVY)


def render():
    page = Page()

    # Masthead: the name of the paper and the date it sums up, big and plain.
    page.fill(0, 0, SIZE, 150, NAVY)
    page.put_text(40, 26, "THE WORLD IN ONE DAY", 6, BAND_TEXT)
    page.put_text(40, 92, "TUESDAY 24 NOVEMBER 2026", 5, BAND_TEXT)
    page.fill(0, 150, SIZE, 6, RED)

    # Lead story: kicker, headline, subline on the left; Capitol art right.
    page.put_text(40, 178, "LEAD STORY", 3, TAG_RED)
    lines = page.wrap_text(LEAD_HEADLINE, 4, 600)
    ly = 214
    for line in lines:
        page.put_text(40, ly, line, 4, INK)
        ly += 36
    sub = page.wrap_text(LEAD_SUB, 3, 600)
    sy = ly + 18
    for line in sub:
        page.put_text(40, sy, line, 3, INK)
        sy += 26
    draw_capitol(page, 664, 172, 320, 248)

    # Eight more stories in a 2 x 4 grid.
    page.fill(0, 436, SIZE, 2, RULE)
    margin, gap = 32, 24
    col_w = (SIZE - 2 * margin - gap) // 2
    row_h = 125
    for i, (tag, headline) in enumerate(GRID):
        col, row = i % 2, i // 2
        tx = margin + col * (col_w + gap)
        ty = 452 + row * row_h
        if row:
            page.fill(tx, ty - 9, col_w, 2, RULE)
        page.fill(tx, ty + 2, 10, 10, RED)
        page.put_text(tx + 18, ty, tag, 3, TAG_RED)
        story_lines = page.wrap_text(headline, 3, col_w - 4)
        hy = ty + 30
        for line in story_lines[:3]:
            page.put_text(tx, hy, line, 3, INK)
            hy += 25

    # Footer: the date once more, so the day is unmistakable.
    page.fill(0, 964, SIZE, 6, RED)
    page.put_text(40, 982, "TUESDAY 24 NOVEMBER 2026 - ONE IMAGE, ONE DAY", 3, INK)
    return page.buf


def encode_png(pixels):
    scanlines = b"".join(
        b"\x00" + bytes(pixels[r * SIZE * 3:(r + 1) * SIZE * 3])
        for r in range(SIZE)
    )

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))


def build():
    return encode_png(render())
