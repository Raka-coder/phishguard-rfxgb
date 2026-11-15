"""Token tampilan PhishGuard: gaya Persona 5 (hitam, merah, putih, bentuk miring).

Nama token lama (PURPLE, CARD, dst.) dipertahankan supaya halaman lain tidak perlu
diubah: nilainya dipetakan ke palet Persona 5.

Aturan warna:
- RED (aksen) : identitas, tombol utama, seri grafik Model B
- WHITE       : seri grafik Model A, border kartu
- PHISH_RED   : phishing, error, risiko naik
- GREEN       : legit, risiko turun
"""

import reflex as rx

# --- Permukaan --------------------------------------------------------------
BG_PAGE = "#0B0B0B"
WINDOW = "#0B0B0B"
SIDEBAR = "#000000"
CARD = "#000000"
CARD_2 = "#1A1A1A"
LINE = "#3A3A3A"
INPUT_BG = "#FFFFFF"

# --- Teks -------------------------------------------------------------------
TEXT = "#FFFFFF"
MUTED = "#C9C9C9"
WHITE = "#FFFFFF"
BLACK = "#000000"

# --- Aksen ------------------------------------------------------------------
P5_RED = "#E60012"
PURPLE = P5_RED            # nama lama: aksen utama
PURPLE_LIGHT = "#FF4455"   # teks/ikon aksen di atas hitam
PURPLE_DEEP = "#7A0009"
RED = "#FF4455"            # phishing (teks/grafik di atas hitam)
RED_SOLID = "#E60012"      # latar badge dengan teks putih
ORANGE = "#FFFFFF"         # seri kedua di grafik (putih)
YELLOW = "#FFD400"
GREEN = "#4ADE80"
GREEN_SOLID = "#15803D"
NEUTRAL_SOLID = "#3B3B3B"

GRADIENT = P5_RED  # tombol/penanda utama: merah solid
PAGE_GLOW = (
    "radial-gradient(#2A2A2A 2px, transparent 2px) 0 0 / 14px 14px, "
    "linear-gradient(115deg, #E60012 0 22%, transparent 22.1%)"
)

# --- Tipografi --------------------------------------------------------------
FONT = "'Times New Roman', Times, serif"
DISPLAY_FONT = "'P5', Impact, 'Arial Black', sans-serif"
SERIF_FONT = "'Times New Roman', Times, serif"
HEAVY_FONT = "'Times New Roman', Times, serif"
MONO_FONT = "'Times New Roman', Times, serif"  # hanya 2 font: Persona 5 + Times New Roman
STYLESHEETS = ["/p5.css"]

# --- Tema Radix + style global ---------------------------------------------
THEME = rx.theme(appearance="dark", accent_color="red", gray_color="gray", radius="none")
APP_STYLE = {"font_family": FONT, "font_size": "18px"}

# --- Kompatibilitas nama lama ----------------------------------------------
LINK_COLOR = PURPLE_LIGHT
ERROR_COLOR = RED
SUCCESS_COLOR = GREEN
ACCENT_COLOR = "red"
