"""
Generates two image types for NORMA's X/Twitter posts:
  1. Game Alert Card  – a branded 1200×675 graphic with live odds
  2. App Mockup       – a phone-frame "screenshot" of the NORMA UI
"""

from __future__ import annotations

import os
import math
from io import BytesIO
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from sports_data import Game, format_moneyline

# ── brand palette ────────────────────────────────────────────────────────────
BG_DARK = (10, 10, 20)
BG_CARD = (18, 18, 35)
BG_CARD2 = (24, 24, 44)
ACCENT = (0, 212, 255)        # electric cyan
ACCENT2 = (0, 255, 135)       # electric green
TEXT_PRIMARY = (255, 255, 255)
TEXT_SECONDARY = (160, 165, 190)
TEXT_DIM = (90, 95, 120)
DIVIDER = (35, 35, 60)
POSITIVE = (0, 220, 100)
NEGATIVE = (255, 75, 75)

# ── font helpers ─────────────────────────────────────────────────────────────
_FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REGULAR
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _centered_x(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, width: int) -> int:
    tw, _ = _text_size(draw, text, font)
    return (width - tw) // 2


# ── rounded rectangle helper ─────────────────────────────────────────────────
def _rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill=None, outline=None, width: int = 1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


# ── pill badge ───────────────────────────────────────────────────────────────
def _badge(draw: ImageDraw.Draw, text: str, x: int, y: int, bg: tuple, fg: tuple, font_size: int = 18):
    font = _font(font_size, bold=True)
    tw, th = _text_size(draw, text, font)
    pad_x, pad_y = 14, 6
    _rounded_rect(draw, (x, y, x + tw + pad_x * 2, y + th + pad_y * 2), radius=20, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return tw + pad_x * 2, th + pad_y * 2


# ─────────────────────────────────────────────────────────────────────────────
# 1.  GAME ALERT CARD  (1200 × 675)
# ─────────────────────────────────────────────────────────────────────────────
def generate_game_alert_card(games: list[Game]) -> BytesIO:
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # gradient-like top strip
    for i in range(6):
        alpha = int(80 * (1 - i / 6))
        draw.rectangle([(0, i), (W, i + 1)], fill=(*ACCENT, alpha))

    # header
    draw.text((48, 32), "NORMA", font=_font(42, bold=True), fill=TEXT_PRIMARY)
    draw.text((48 + _text_size(draw, "NORMA", _font(42, bold=True))[0] + 10, 44),
              "Sports Alerts & Wager Tracker", font=_font(22), fill=TEXT_SECONDARY)

    _badge(draw, "TODAY'S GAMES", W - 220, 32, ACCENT, BG_DARK, font_size=18)

    # divider
    draw.line([(48, 90), (W - 48, 90)], fill=DIVIDER, width=1)

    visible_games = games[:3]
    if not visible_games:
        msg = "No games scheduled today"
        draw.text((_centered_x(draw, msg, _font(28), W), H // 2 - 20),
                  msg, font=_font(28), fill=TEXT_SECONDARY)
        return _to_bytes(img)

    row_h = (H - 120 - 80) // len(visible_games)
    for idx, game in enumerate(visible_games):
        y = 110 + idx * row_h
        _draw_game_row(draw, game, 48, y, W - 96, row_h - 12)

    # footer
    footer_y = H - 52
    draw.line([(48, footer_y - 14), (W - 48, footer_y - 14)], fill=DIVIDER, width=1)
    # No domain is printed here. An earlier version rendered "norma.app", which is
    # a live site belonging to an unrelated analytics company, and "norma-app.com"
    # is likewise a different business. Printing an unverified domain on NORMA's
    # own marketing assets sends viewers to someone else. Restore a URL here only
    # once NORMA controls the domain and it resolves to NORMA.
    draw.text((48, footer_y), "Track every alert on NORMA",
              font=_font(20), fill=TEXT_DIM)
    store_text = "App Store & Google Play"
    draw.text((W - 48 - _text_size(draw, store_text, _font(20))[0], footer_y),
              store_text, font=_font(20), fill=ACCENT)

    return _to_bytes(img)


def _draw_game_row(draw: ImageDraw.Draw, game: Game, x: int, y: int, w: int, h: int):
    # card background
    _rounded_rect(draw, (x, y, x + w, y + h), radius=12, fill=BG_CARD)

    em = game.sport_emoji
    draw.text((x + 18, y + h // 2 - 14), em, font=_font(28), fill=TEXT_PRIMARY)

    # teams
    away = game.away_team.split()[-1].upper()
    home = game.home_team.split()[-1].upper()
    matchup = f"{away}  vs  {home}"
    draw.text((x + 62, y + 12), matchup, font=_font(24, bold=True), fill=TEXT_PRIMARY)
    draw.text((x + 62, y + 42), game.time_str, font=_font(18), fill=TEXT_SECONDARY)

    # odds columns
    col_w = 140
    col_start = x + w - col_w * 3 - 20

    # spread
    _odds_col(draw, "SPREAD", f"{game.spread:+.1f}" if game.spread else "N/A",
              f"({format_moneyline(game.spread_home_odds)})" if game.spread_home_odds else "",
              col_start, y, col_w, h)

    # moneyline
    home_ml = format_moneyline(game.home_moneyline)
    away_ml = format_moneyline(game.away_moneyline)
    _odds_col(draw, "MONEYLINE", home_ml, f"away {away_ml}",
              col_start + col_w + 10, y, col_w, h)

    # total
    _odds_col(draw, "TOTAL", f"O/U {game.over_under}" if game.over_under else "N/A", "",
              col_start + (col_w + 10) * 2, y, col_w, h)


def _odds_col(draw: ImageDraw.Draw, label: str, value: str, sub: str,
              x: int, y: int, w: int, h: int):
    draw.text((x + 8, y + 10), label, font=_font(14, bold=True), fill=TEXT_DIM)
    color = POSITIVE if value.startswith("+") else (NEGATIVE if value.startswith("-") else TEXT_PRIMARY)
    draw.text((x + 8, y + 28), value, font=_font(20, bold=True), fill=color)
    if sub:
        draw.text((x + 8, y + 52), sub, font=_font(14), fill=TEXT_SECONDARY)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  APP MOCKUP  (phone frame with NORMA UI, 630 × 1200)
# ─────────────────────────────────────────────────────────────────────────────
def generate_app_mockup(games: list[Game]) -> BytesIO:
    W, H = 630, 1200
    img = Image.new("RGB", (W, H), (8, 8, 16))
    draw = ImageDraw.Draw(img)

    # subtle glow behind phone
    for r in range(220, 0, -20):
        alpha = int(18 * (r / 220))
        draw.ellipse([(W // 2 - r, H // 2 - r * 2), (W // 2 + r, H // 2 + r * 2)],
                     fill=(*ACCENT, alpha))

    # phone body
    px, py = 55, 60
    pw, ph = W - px * 2, H - py * 2
    _rounded_rect(draw, (px, py, px + pw, py + ph), radius=48,
                  fill=(22, 22, 38), outline=(55, 55, 80), width=3)

    # side buttons
    draw.rounded_rectangle([px - 5, py + 180, px - 1, py + 240], radius=3, fill=(45, 45, 65))
    draw.rounded_rectangle([px + pw + 1, py + 140, px + pw + 5, py + 190], radius=3, fill=(45, 45, 65))
    draw.rounded_rectangle([px + pw + 1, py + 210, px + pw + 5, py + 300], radius=3, fill=(45, 45, 65))

    # screen area
    sx, sy = px + 12, py + 12
    sw, sh = pw - 24, ph - 24
    _rounded_rect(draw, (sx, sy, sx + sw, sy + sh), radius=38, fill=BG_DARK)

    # dynamic island
    di_w, di_h = 120, 32
    draw.rounded_rectangle(
        [sx + sw // 2 - di_w // 2, sy + 12, sx + sw // 2 + di_w // 2, sy + 12 + di_h],
        radius=16, fill=(0, 0, 0))

    # status bar
    bar_y = sy + 55
    draw.text((sx + 24, bar_y), "9:41", font=_font(20, bold=True), fill=TEXT_PRIMARY)
    # signal/wifi/battery icons (drawn as simple shapes)
    _draw_status_icons(draw, sx + sw - 90, bar_y, sw)

    # app header
    header_y = bar_y + 34
    draw.text((sx + 24, header_y), "NORMA", font=_font(32, bold=True), fill=TEXT_PRIMARY)
    sub_x = sx + 24 + _text_size(draw, "NORMA", _font(32, bold=True))[0] + 10
    draw.text((sub_x, header_y + 8), "alerts", font=_font(20), fill=ACCENT)
    # notification bell icon
    _draw_bell(draw, sx + sw - 50, header_y + 4)

    # tab bar (just under header)
    tab_y = header_y + 48
    tabs = ["Alerts", "My Wagers", "Scores", "Explore"]
    tab_w = sw // len(tabs)
    for i, tab in enumerate(tabs):
        tx = sx + i * tab_w
        active = i == 0
        color = ACCENT if active else TEXT_DIM
        tw, _ = _text_size(draw, tab, _font(18, bold=active))
        draw.text((tx + (tab_w - tw) // 2, tab_y), tab, font=_font(18, bold=active), fill=color)
        if active:
            draw.line([(tx + (tab_w - tw) // 2, tab_y + 24),
                       (tx + (tab_w + tw) // 2, tab_y + 24)], fill=ACCENT, width=2)

    # section label
    sec_y = tab_y + 40
    draw.text((sx + 24, sec_y), "TODAY'S GAME ALERTS", font=_font(14, bold=True), fill=TEXT_DIM)

    # alert cards (show up to 4 games)
    card_y = sec_y + 28
    card_x = sx + 16
    card_w = sw - 32
    for game in games[:4]:
        card_y = _draw_alert_card(draw, game, card_x, card_y, card_w)
        card_y += 10

    # bottom nav bar
    nav_y = sy + sh - 74
    draw.line([(sx, nav_y), (sx + sw, nav_y)], fill=DIVIDER, width=1)
    nav_items = [("🏠", "Home"), ("🔔", "Alerts"), ("💰", "Wagers"), ("👤", "Profile")]
    nav_w = sw // len(nav_items)
    for i, (icon, label) in enumerate(nav_items):
        nx = sx + i * nav_w + nav_w // 2
        active = i == 1
        color = ACCENT if active else TEXT_DIM
        iw, _ = _text_size(draw, icon, _font(22))
        draw.text((nx - iw // 2, nav_y + 8), icon, font=_font(22), fill=color)
        lw, _ = _text_size(draw, label, _font(14))
        draw.text((nx - lw // 2, nav_y + 36), label, font=_font(14, bold=active), fill=color)

    return _to_bytes(img)


def _draw_alert_card(draw: ImageDraw.Draw, game: Game, x: int, y: int, w: int) -> int:
    h = 88
    _rounded_rect(draw, (x, y, x + w, y + h), radius=14, fill=BG_CARD2)

    # left accent bar
    draw.rounded_rectangle([x, y + 12, x + 3, y + h - 12], radius=2, fill=ACCENT)

    # sport emoji + teams
    draw.text((x + 16, y + 12), game.sport_emoji, font=_font(24), fill=TEXT_PRIMARY)
    away = game.away_team.split()[-1]
    home = game.home_team.split()[-1]
    matchup = f"{away} @ {home}"
    draw.text((x + 50, y + 10), matchup, font=_font(20, bold=True), fill=TEXT_PRIMARY)
    draw.text((x + 50, y + 35), game.time_str, font=_font(15), fill=TEXT_SECONDARY)

    # odds pill
    ml = format_moneyline(game.home_moneyline)
    ml_color = POSITIVE if game.home_moneyline and game.home_moneyline > 0 else NEGATIVE
    _badge(draw, f"ML {ml}", x + w - 100, y + 28, BG_DARK, ml_color, font_size=15)

    # "Track" button
    btn_text = "Track"
    btn_w, btn_h = 72, 28
    _rounded_rect(draw, (x + w - 84, y + h - 38, x + w - 12, y + h - 10),
                  radius=14, fill=ACCENT)
    tw, th = _text_size(draw, btn_text, _font(14, bold=True))
    draw.text((x + w - 84 + (btn_w - tw) // 2, y + h - 38 + (btn_h - th) // 2),
              btn_text, font=_font(14, bold=True), fill=BG_DARK)

    return y + h


def _draw_status_icons(draw: ImageDraw.Draw, x: int, y: int, sw: int):
    # battery
    bx, by = x + 54, y + 2
    draw.rounded_rectangle([bx, by, bx + 28, by + 14], radius=3,
                            outline=TEXT_SECONDARY, width=1)
    draw.rectangle([bx + 29, by + 4, bx + 31, by + 10], fill=TEXT_SECONDARY)
    draw.rectangle([bx + 2, by + 2, bx + 24, by + 12], fill=POSITIVE)
    # wifi
    wx, wy = x + 28, y
    for r in [14, 9, 4]:
        draw.arc([(wx - r, wy), (wx + r, wy + r * 1.2)], start=200, end=340,
                 fill=TEXT_SECONDARY, width=2)
    draw.ellipse([(wx - 2, wy + 12), (wx + 2, wy + 16)], fill=TEXT_SECONDARY)
    # signal bars
    for i, bar_h in enumerate([4, 7, 10, 13]):
        bx2 = x + i * 5
        draw.rectangle([bx2, wy + 14 - bar_h, bx2 + 3, wy + 14],
                       fill=TEXT_SECONDARY if i < 3 else TEXT_DIM)


def _draw_bell(draw: ImageDraw.Draw, x: int, y: int):
    draw.arc([(x, y), (x + 22, y + 20)], start=0, end=180, fill=ACCENT, width=2)
    draw.line([(x, y + 10), (x, y + 22)], fill=ACCENT, width=2)
    draw.line([(x + 22, y + 10), (x + 22, y + 22)], fill=ACCENT, width=2)
    draw.line([(x, y + 22), (x + 22, y + 22)], fill=ACCENT, width=2)
    draw.arc([(x + 7, y + 20), (x + 15, y + 28)], start=0, end=180, fill=ACCENT, width=2)
    # notification dot
    draw.ellipse([(x + 14, y - 4), (x + 24, y + 6)], fill=NEGATIVE)


def _to_bytes(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
