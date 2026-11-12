"""Generate pocketledger's visual assets with PIL (no network, no fonts).

- assets/terminal-demo.png — a terminal-style screenshot of the demo run,
  used as the README hero.
- assets/social-preview.png — 1280x640 GitHub social preview.

Usage: python3 tools/make_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = (13, 17, 23)
PANEL = (22, 27, 34)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
AMBER = (210, 153, 34)
BLUE = (88, 166, 255)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)
WHITE = (255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def terminal_demo() -> None:
    lines: list[tuple[str, tuple[int, int, int]]] = [
        ("$ pocketledger report --month 2026-11", MUTED),
        ("", TEXT),
        ("# pocketledger — 2026-11", WHITE),
        ("", TEXT),
        ("- Income:   $6,400.00", GREEN),
        ("- Spending: $231.27", RED),
        ("- Saved:    $6,168.73  (96.4% savings rate)", GREEN),
        ("", TEXT),
        ("Spending by category", WHITE),
        ("  Groceries      2 txns   $151.20  ████████████", TEXT),
        ("  Subscriptions  3 txns    $42.97  ███", TEXT),
        ("  Transport      2 txns    $26.60  ██", TEXT),
        ("  Dining         2 txns    $10.50  █", TEXT),
        ("", TEXT),
        ("$ pocketledger recurring", MUTED),
        ("recurring charges — est. $15.49 / month in spending", TEXT),
        ("netflix   -$15.49  every ~30d  x5  ≈ $15.49/mo", AMBER),
        ("", TEXT),
        ("$ pocketledger doctor", MUTED),
        ("transactions: 23   uncategorized: 0   OK", GREEN),
    ]
    font = _font(20)
    bold = _font(20)
    pad_x, pad_y, line_h = 28, 26, 30
    width = 980
    height = pad_y * 2 + line_h * len(lines) + 42
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    # Title bar
    draw.rounded_rectangle([0, 0, width, 42], radius=12, fill=PANEL)
    draw.rectangle([0, 30, width, 42], fill=PANEL)
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse([18 + i * 24, 13, 30 + i * 24, 25], fill=color)
    draw.text((110, 12), "pocketledger — demo", font=_font(16), fill=MUTED)
    y = 42 + pad_y
    for text, color in lines:
        draw.text((pad_x, y), text, font=font, fill=color)
        y += line_h
    img.save(ASSETS / "terminal-demo.png")
    print(f"wrote {ASSETS / 'terminal-demo.png'} ({width}x{height})")


def social_preview() -> None:
    width, height = 1280, 640
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    # Accent bar + subtle panel
    draw.rectangle([0, 0, width, 8], fill=GREEN)
    draw.rounded_rectangle([70, 150, 1210, 565], radius=24, fill=PANEL)
    title = _font(84)
    tag = _font(34)
    small = _font(26)
    draw.text((110, 190), "pocketledger", font=title, fill=WHITE)
    draw.text(
        (110, 300),
        "Your money, your disk, your rules.",
        font=tag,
        fill=GREEN,
    )
    draw.text(
        (110, 360),
        "Local-first personal finance ledger — bank CSV import, budgets,",
        font=small,
        fill=TEXT,
    )
    draw.text(
        (110, 398),
        "subscription audit & net worth. Zero deps, zero cloud.",
        font=small,
        fill=TEXT,
    )
    # Stat chips
    chips = [("$0", "monthly cost"), ("0", "trackers"), ("100%", "local")]
    x = 110
    for value, label in chips:
        draw.rounded_rectangle([x, 460, x + 150, 535], radius=12, fill=BG)
        draw.text((x + 18, 472), value, font=_font(30), fill=BLUE)
        draw.text((x + 18, 505), label, font=_font(16), fill=MUTED)
        x += 170
    draw.text((110, 590), "github.com/BidyutRoy2/pocketledger", font=_font(22), fill=MUTED)
    img.save(ASSETS / "social-preview.png")
    print(f"wrote {ASSETS / 'social-preview.png'} ({width}x{height})")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    terminal_demo()
    social_preview()
