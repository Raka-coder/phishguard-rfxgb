"""Token tampilan PhishGuard: dashboard gelap ungu (referensi Nightfall).

Aturan warna:
- PURPLE : identitas, tombol utama, aksen
- RED    : phishing, error, risiko naik
- GREEN  : legit, risiko turun
- ORANGE/YELLOW : seri tambahan di grafik
"""

import reflex as rx

# --- Permukaan --------------------------------------------------------------
BG_PAGE = "#0A0710"
WINDOW = "#100D16"
SIDEBAR = "#0D0A13"
CARD = "#17141E"
CARD_2 = "#1E1A27"
LINE = "#2B2736"
INPUT_BG = "#0E0B14"

# --- Teks -------------------------------------------------------------------
TEXT = "#F2F0F8"
MUTED = "#A19BB5"
WHITE = "#FFFFFF"

# --- Aksen ------------------------------------------------------------------
PURPLE = "#8B5CF6"
PURPLE_LIGHT = "#B79CFF"
PURPLE_DEEP = "#4C1D95"
RED = "#EF4444"
RED_SOLID = "#DC2626"     # latar badge dengan teks putih
ORANGE = "#F97316"
YELLOW = "#EAB308"
GREEN = "#22C55E"
GREEN_SOLID = "#15803D"   # latar badge dengan teks putih
NEUTRAL_SOLID = "#3B3748"

GRADIENT = "linear-gradient(135deg, #6D3BE0 0%, #9B67FF 100%)"
PAGE_GLOW = (
    "radial-gradient(900px 520px at 88% -8%, rgba(139,92,246,0.38), transparent 60%), "
    "radial-gradient(760px 520px at -6% 108%, rgba(91,33,182,0.38), transparent 60%)"
)

# --- Tipografi --------------------------------------------------------------
FONT = "'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif"
MONO_FONT = "ui-monospace, 'Cascadia Code', Consolas, monospace"
STYLESHEETS = [
    "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
]

# --- Tema Radix + style global ---------------------------------------------
THEME = rx.theme(appearance="dark", accent_color="violet", gray_color="slate", radius="large")
APP_STYLE = {"font_family": FONT}

# --- Kompatibilitas nama lama ----------------------------------------------
LINK_COLOR = PURPLE_LIGHT
ERROR_COLOR = RED
SUCCESS_COLOR = GREEN
ACCENT_COLOR = "violet"
