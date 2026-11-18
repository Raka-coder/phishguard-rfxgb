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
MUTED = "#FFFFFF"  # semua teks biasa (Public Sans) putih
WHITE = "#FFFFFF"
BLACK = "#000000"

# --- Aksen & Status Semantik ------------------------------------------------
P5_RED = "#E60012"
PURPLE = P5_RED            # nama lama: aksen utama
PURPLE_LIGHT = "#FF4455"   # teks/ikon aksen di atas hitam
PURPLE_DEEP = "#7A0009"
RED = "#FF4455"            # phishing (teks/grafik di atas hitam)
RED_SOLID = "#E60012"      # latar badge dengan teks putih
ORANGE = "#FFFFFF"         # seri kedua di grafik (putih)
YELLOW = "#F59E0B"         # amber/kuning peringatan tegas untuk suspicious
GREEN = "#4ADE80"
GREEN_SOLID = "#15803D"
NEUTRAL_SOLID = "#3B3B3B"
LEGIT_PANEL = "#333333"  # latar panel gambar legit: hitam sedikit lebih terang

# Status Palettes (WCAG compliant)
STATUS_PHISH_BG = "#3E1215"
STATUS_PHISH_BORDER = "#E60012"
STATUS_PHISH_TEXT = "#FF8A80"

STATUS_SUSP_BG = "#3D2B05"
STATUS_SUSP_BORDER = "#F59E0B"
STATUS_SUSP_TEXT = "#FDE68A"

STATUS_LEGIT_BG = "#0D331E"
STATUS_LEGIT_BORDER = "#15803D"
STATUS_LEGIT_TEXT = "#86EFAC"

GRADIENT = P5_RED  # tombol/penanda utama: merah solid
PAGE_GLOW = (
    "radial-gradient(#2A2A2A 2px, transparent 2px) 0 0 / 14px 14px, "
    "linear-gradient(115deg, #E60012 0 22%, transparent 22.1%)"
)

# --- Tipografi --------------------------------------------------------------
FONT = "'Public Sans', system-ui, sans-serif"
DISPLAY_FONT = "'P5', Impact, 'Arial Black', sans-serif"
SERIF_FONT = FONT  # nama lama; sekarang Public Sans
HEAVY_FONT = FONT
MONO_FONT = FONT  # hanya 2 font: Persona 5 + Public Sans
STYLESHEETS = ["/p5.css"]

# --- Tema Radix + style global ---------------------------------------------
THEME = rx.theme(appearance="dark", accent_color="red", gray_color="gray", radius="none")
APP_STYLE = {"font_family": FONT, "font_size": "16px", "font_weight": "500", "color": TEXT}

# --- Kompatibilitas nama lama ----------------------------------------------
LINK_COLOR = PURPLE_LIGHT
ERROR_COLOR = RED
SUCCESS_COLOR = GREEN
ACCENT_COLOR = "red"
