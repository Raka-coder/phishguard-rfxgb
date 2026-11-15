"""Komponen bersama: kerangka dashboard (sidebar + topbar), kartu, judul kartu."""

import reflex as rx

from app import style as t


def card(*children, **style_overrides) -> rx.Component:
    style = {
        "background": t.CARD,
        "border": f"1px solid {t.LINE}",
        "border_radius": "16px",
        "padding": "20px",
        "width": "100%",
        "min_width": "0",
    }
    style.update(style_overrides)
    return rx.box(*children, style=style)


def card_title(icon: str, text: str) -> rx.Component:
    return rx.hstack(
        rx.icon(icon, size=20, style={"color": t.PURPLE_LIGHT}),
        rx.text(text, style={"font_size": "1.02rem", "font_weight": "600", "color": t.TEXT}),
        align="center",
        spacing="2",
    )


def muted(text, **kw) -> rx.Component:
    return rx.text(text, size=kw.pop("size", "2"), style={"color": t.MUTED, **kw.pop("style", {})}, **kw)


def _nav_item(icon: str, label: str, href: str, active: bool) -> rx.Component:
    return rx.tooltip(
        rx.link(
            rx.icon(icon, size=20),
            href=href,
            underline="none",
            style={
                "display": "flex",
                "align_items": "center",
                "justify_content": "center",
                "width": "44px",
                "height": "44px",
                "border_radius": "12px",
                "color": t.PURPLE_LIGHT if active else t.MUTED,
                "background": t.CARD_2 if active else "transparent",
                "box_shadow": f"inset 3px 0 0 {t.PURPLE}" if active else "none",
                "&:hover": {"background": t.CARD_2, "color": t.TEXT},
            },
        ),
        content=label,
    )


def sidebar(active: str) -> rx.Component:
    return rx.flex(
        _nav_item("shield-check", "Cek URL", "/", active == "cek"),
        _nav_item("activity", "Evaluasi model", "/evaluasi", active == "evaluasi"),
        direction="column",
        align="center",
        gap="12px",
        style={
            "width": "72px",
            "flex_shrink": "0",
            "padding": "20px 0",
            "background": t.SIDEBAR,
            "border_right": f"1px solid {t.LINE}",
        },
    )


def topbar(subtitle: str) -> rx.Component:
    return rx.flex(
        rx.hstack(
            rx.box(
                rx.icon("shield-check", size=20, style={"color": t.WHITE}),
                style={"background": t.GRADIENT, "padding": "8px", "border_radius": "10px", "display": "flex"},
            ),
            rx.text("PhishGuard", style={"font_size": "1.25rem", "font_weight": "700", "color": t.TEXT}),
            align="center",
            spacing="3",
        ),
        rx.spacer(),
        rx.text(subtitle, size="2", style={"color": t.MUTED}),
        align="center",
        style={"height": "68px", "padding": "0 24px", "border_bottom": f"1px solid {t.LINE}"},
    )


def page_shell(*children, active: str = "cek", subtitle: str = "") -> rx.Component:
    window = rx.flex(
        sidebar(active),
        rx.box(
            topbar(subtitle),
            rx.box(*children, style={"padding": "24px"}),
            style={"flex": "1", "min_width": "0"},
        ),
        style={
            "max_width": "1240px",
            "margin": "0 auto",
            "background": t.WINDOW,
            "border": f"1px solid {t.LINE}",
            "border_radius": "24px",
            "overflow": "hidden",
            "min_height": "calc(100vh - 48px)",
            "box_shadow": "0 24px 80px rgba(0,0,0,0.55)",
        },
    )
    return rx.box(
        window,
        style={
            "min_height": "100vh",
            "padding": "24px",
            "background": f"{t.PAGE_GLOW}, {t.BG_PAGE}",
            "color": t.TEXT,
            "font_family": t.FONT,
        },
    )
