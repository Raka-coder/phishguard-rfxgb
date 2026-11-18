"""Komponen bersama gaya Persona 5: kerangka halaman (header miring), kartu, judul kartu."""

import reflex as rx

from app import style as t

DISPLAY = {"font_family": t.DISPLAY_FONT, "text_transform": "uppercase", "letter_spacing": "1px", "text_shadow": "none"}


def card(*children, **style_overrides) -> rx.Component:
    style = {
        "background": t.CARD,
        "border": f"5px solid {t.WHITE}",
        "box_shadow": f"8px 8px 0 {t.P5_RED}",
        "border_radius": "0",
        "padding": "20px",
        "width": "100%",
        "min_width": "0",
    }
    style.update(style_overrides)
    return rx.box(*children, style=style)


def card_title(icon: str, text: str) -> rx.Component:
    """Penanda merah miring; isinya ditegakkan lagi (counter-skew)."""
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=20, style={"color": t.WHITE}),
            rx.text(
                text,
                style={"font_family": t.SERIF_FONT, "font_weight": "800", "text_transform": "uppercase", "letter_spacing": "1.5px", "font_size": "1.05rem", "color": t.WHITE, "text_shadow": f"2px 2px 0 {t.BLACK}"},
            ),
            align="center",
            spacing="2",
            style={"transform": "skewX(14deg)"},
        ),
        style={
            "display": "inline-block",
            "background": t.P5_RED,
            "padding": "4px 18px",
            "transform": "skewX(-14deg)",
        },
    )


def p5_callout(content, icon: str = "info", warn: bool = False) -> rx.Component:
    """Pengganti rx.callout: info = hitam + garis merah; warn = merah solid. Gaya Persona 5."""
    return rx.hstack(
        rx.icon(icon, size=22, style={"color": t.WHITE if warn else t.P5_RED, "flex_shrink": "0"}),
        rx.text(content, style={"color": t.WHITE, "font_weight": "600"}),
        align="center",
        spacing="3",
        style={
            "width": "100%",
            "background": t.P5_RED if warn else t.BLACK,
            "border": f"3px solid {t.WHITE}",
            "border_left": f"12px solid {t.WHITE if warn else t.P5_RED}",
            "border_radius": "0",
            "padding": "12px 18px",
            "box_shadow": f"6px 6px 0 {t.BLACK if warn else '#333333'}",
        },
    )


def muted(text, **kw) -> rx.Component:
    return rx.text(text, size=kw.pop("size", "2"), style={"color": t.MUTED, **kw.pop("style", {})}, **kw)


def _nav_item(label: str, href: str, active: bool) -> rx.Component:
    return rx.link(
        rx.text(label, style={**DISPLAY, "font_size": "1.25rem", "transform": "skewX(12deg)"}),
        href=href,
        underline="none",
        style={
            "display": "inline-block",
            "padding": "8px 26px",
            "transform": "skewX(-12deg)",
            "background": t.WHITE if active else t.BLACK,
            "color": t.P5_RED if active else t.WHITE,
            "border": f"3px solid {t.P5_RED if active else t.WHITE}",
            "&:hover": {"background": t.P5_RED, "color": t.WHITE, "border_color": t.WHITE},
        },
    )


def topbar(active: str, subtitle: str) -> rx.Component:
    return rx.flex(
        rx.box(
            rx.text("PhishGuard", style={**DISPLAY, "font_size": "1.9rem", "color": t.BLACK}),
            style={"background": t.WHITE, "padding": "4px 22px", "transform": "rotate(-3deg)"},
        ),
        rx.text(
            subtitle,
            size="2",
            style={"color": t.WHITE, "background": t.BLACK, "padding": "6px 12px", "display": {"initial": "none", "md": "block"}},
        ),
        rx.spacer(),
        rx.hstack(
            _nav_item("Cek URL", "/", active == "cek"),
            _nav_item("Evaluasi", "/evaluasi", active == "evaluasi"),
            spacing="3",
            wrap="wrap",
        ),
        align="center",
        gap="16px",
        wrap="wrap",
        style={"padding": "24px 32px"},
    )


def page_shell(*children, active: str = "cek", subtitle: str = "") -> rx.Component:
    return rx.box(
        topbar(active, subtitle),
        rx.box(
            *children,
            style={"max_width": "1240px", "margin": "0 auto", "padding": "8px 32px 48px"},
        ),
        style={
            "min_height": "100vh",
            "background": f"{t.PAGE_GLOW}, {t.BG_PAGE}",
            "color": t.TEXT,
            "font_family": t.FONT,
        },
    )
