"""Halaman index: input URL, kartu verdict, donut probabilitas, dan fitur berpengaruh."""

import reflex as rx

from app import style as t
from app.app_state import State
from app.components import card, card_title, muted, p5_callout, page_shell

EXAMPLES = [
    ("Coba contoh mencurigakan", "http://192.168.0.1/paypal-login-verify.xyz"),
    ("Coba contoh legit", "https://www.wikipedia.org"),
]
MONO = {"font_family": t.MONO_FONT}


def example_chip(label: str, url: str) -> rx.Component:
    return rx.button(
        label,
        type="button",
        variant="outline",
        size="2",
        disabled=State.loading,
        on_click=State.use_example(url),
        style={
            "cursor": "pointer",
            "color": t.TEXT,
            "background": t.BLACK,
            "box_shadow": f"inset 0 0 0 2px {t.WHITE}",
            "&:hover": {"box_shadow": f"inset 0 0 0 2px {t.P5_RED}", "color": t.PURPLE_LIGHT},
        },
    )


def search_card() -> rx.Component:
    return card(
        card_title("link", "Periksa URL"),
        muted(
            "PhishGuard membaca 19 ciri dari teks URL dan menghitung peluang phishing. "
            "Situsnya tidak dibuka atau dipindai.",
            style={"margin_top": "6px", "margin_bottom": "16px"},
        ),
        rx.form.root(
            rx.flex(
                rx.input(
                    rx.input.slot(rx.icon("search", size=18)),
                    name="url",
                    value=State.url,
                    on_change=State.set_url,
                    placeholder="https://contoh.com/login",
                    size="3",
                    style={
                        "flex": "1",
                        "width": "100%",
                        "background": t.INPUT_BG,
                        "box_shadow": f"6px 6px 0 {t.P5_RED}",
                        "border": f"4px solid {t.BLACK}",
                        "color": t.BLACK,
                        "text_shadow": "none",
                        "font_weight": "700",
                    },
                ),
                rx.button(
                    "Periksa URL",
                    type="submit",
                    size="3",
                    loading=State.loading,
                    disabled=State.loading,
                    style={
                        "cursor": "pointer",
                        "background": t.BLACK,
                        "color": t.P5_RED,
                        "font_family": t.DISPLAY_FONT,
                        "text_shadow": "none",
                        "text_transform": "uppercase",
                        "font_size": "1.35rem",
                        "padding": "0 32px",
                        "border": f"4px solid {t.WHITE}",
                        "transform": "skewX(-8deg)",
                        "box_shadow": f"6px 6px 0 {t.P5_RED}",
                        "&:hover": {"background": t.P5_RED, "color": t.WHITE},
                    },
                ),
                direction={"initial": "column", "sm": "row"},
                gap="3",
            ),
            on_submit=State.check_url,
            reset_on_submit=False,
            width="100%",
        ),
        rx.hstack(
            muted("Atau"),
            *[example_chip(label, url) for label, url in EXAMPLES],
            align="center",
            wrap="wrap",
            spacing="2",
            margin_top="14px",
        ),
    )


def error_callout() -> rx.Component:
    return p5_callout(State.error, icon="triangle-alert", warn=True)


def empty_state() -> rx.Component:
    return card(
        rx.vstack(
            rx.box(
                rx.icon("shield-check", size=34, style={"color": t.PURPLE_LIGHT}),
                style={"background": t.CARD_2, "padding": "16px", "border_radius": "0", "display": "flex"},
            ),
            rx.text("Belum ada URL yang diperiksa", style={"font_size": "1.05rem", "font_weight": "600"}),
            muted("Tempel URL di atas atau pakai salah satu contoh. Hasilnya muncul di sini."),
            align="center",
            spacing="3",
            style={"padding": "36px 0"},
        ),
    )


def verdict_card() -> rx.Component:
    return card(
        rx.hstack(
            rx.box(style={"width": "4px", "height": "16px", "background": State.verdict_color, "border_radius": "0"}),
            muted("Verdict"),
            align="center",
            spacing="2",
        ),
        rx.hstack(
            rx.box(
                rx.image(
                    src=rx.cond(
                        State.is_phishing,
                        "/img/phishing.png",
                        rx.cond(State.label_name == "SUSPICIOUS", "/img/suspicious.png", "/img/legit.png"),
                    ),
                    alt=State.display_label,
                    style={"width": "100%", "height": "100%", "object_fit": "contain", "object_position": "bottom"},
                ),
                style={
                    "width": "112px",
                    "height": "120px",
                    "flex_shrink": "0",
                    "background": rx.cond(
                        State.is_phishing,
                        t.P5_RED,
                        rx.cond(State.label_name == "SUSPICIOUS", t.YELLOW, t.LEGIT_PANEL),
                    ),
                    "clip_path": "polygon(12% 0, 100% 0, 88% 100%, 0 100%)",
                    "overflow": "hidden",
                },
            ),
            rx.vstack(
                rx.text(
                    State.display_label,
                    style={"font_family": t.DISPLAY_FONT, "text_shadow": "none", "text_transform": "uppercase", "font_size": "1.6rem", "line_height": "1.1", "color": State.verdict_color, "overflow_wrap": "anywhere"},
                ),
                muted(State.verdict_note),
                rx.hstack(
                    rx.badge(
                        State.risk_label,
                        style={"background": State.risk_color, "color": t.BLACK, "border_radius": "0", "font_weight": "800"},
                    ),
                    rx.badge(State.decision_source, color_scheme="gray", variant="soft"),
                    spacing="2",
                ),
                spacing="1",
                align="start",
                style={"min_width": "0", "flex": "1"},
            ),
            align="center",
            spacing="4",
            margin_top="18px",
        ),
        rx.box(
            muted("URL yang diperiksa", size="1"),
            rx.text(State.submitted_url, size="2", style={**MONO, "color": t.WHITE, "word_break": "break-all", "margin_top": "2px"}),
            style={
                "background": t.CARD_2,
                "border": f"2px solid {t.WHITE}",
                "border_radius": "0",
                "padding": "10px 12px",
                "margin_top": "18px",
            },
        ),
    )


def probability_card() -> rx.Component:
    return card(
        card_title("activity", "Peluang phishing (Model B)"),
        rx.cond(
            State.probability_pct != "—",
            rx.box(
                rx.recharts.pie_chart(
                    rx.recharts.pie(
                        data=State.prob_data,
                        data_key="value",
                        name_key="name",
                        inner_radius=62,
                        outer_radius=84,
                        start_angle=90,
                        end_angle=-270,
                        stroke="none",
                    ),
                    width="100%",
                    height=210,
                ),
                rx.flex(
                    rx.text(
                        State.probability_pct,
                        style={"font_size": "1.6rem", "font_weight": "700", "line_height": "1.1"},
                    ),
                    muted("phishing", size="1"),
                    direction="column",
                    align="center",
                    justify="center",
                    style={"position": "absolute", "inset": "0", "pointer_events": "none"},
                ),
                style={"position": "relative", "width": "100%", "margin_top": "6px"},
            ),
            rx.box(
                muted("Tidak dihitung (domain tepercaya).", size="2"),
                style={"height": "210px", "display": "flex", "align_items": "center", "justify_content": "center"},
            ),
        ),
        rx.hstack(
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.RED}),
                muted("Phishing", size="1"),
                align="center",
                spacing="1",
            ),
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.GREEN}),
                muted("Legit", size="1"),
                align="center",
                spacing="1",
            ),
            rx.spacer(),
            muted("Skor Model B; ambang label 50%", size="1"),
            width="100%",
        ),
    )


def timing_card() -> rx.Component:
    return card(
        card_title("timer", "Waktu inference"),
        rx.hstack(
            rx.text(State.inference_ms, style={"font_size": "2.6rem", "font_weight": "700", "line_height": "1"}),
            muted("ms"),
            align="end",
            spacing="2",
            margin_top="18px",
        ),
        muted("Waktu model menghitung satu URL.", size="1", style={"margin_top": "10px"}),
    )


def impact_badge(icon: str, text: str, bg: str) -> rx.Component:
    return rx.hstack(
        rx.icon(icon, size=14),
        rx.text(text, size="1", weight="bold"),
        align="center",
        spacing="1",
        style={"background": bg, "color": t.WHITE, "padding": "4px 10px", "border_radius": "0", "white_space": "nowrap"},
    )


def render_feature(item: rx.Var[dict]) -> rx.Component:
    return rx.box(
        rx.flex(
            rx.vstack(
                muted(item["label"], size="2"),
                rx.text(item["feature"], size="1", style={**MONO, "color": t.MUTED, "opacity": "0.8"}),
                spacing="0",
                align="start",
                style={"min_width": "0"},
            ),
            rx.spacer(),
            rx.match(
                item["dir"],
                ("up", impact_badge("arrow-up-right", "Naik", t.RED_SOLID)),
                ("down", impact_badge("arrow-down-right", "Turun", t.GREEN_SOLID)),
                impact_badge("minus", "Netral", t.NEUTRAL_SOLID),
            ),
            align="start",
            gap="3",
        ),
        rx.text(item["value"], style={"font_size": "1.9rem", "font_weight": "600", "margin_top": "12px"}),
        style={
            "background": t.CARD_2,
            "border": f"1px solid {t.LINE}",
            "border_radius": "0",
            "padding": "14px 16px",
        },
    )


def features_card() -> rx.Component:
    return card(
        card_title("layers", "Fitur yang paling berpengaruh"),
        muted(
            "Dibandingkan dengan rata-rata URL legit dan phishing di dataset. "
            "Naik berarti risiko bertambah, turun berarti berkurang.",
            style={"margin_top": "6px", "margin_bottom": "16px"},
        ),
        rx.grid(
            rx.foreach(State.top_features, render_feature),
            columns={"initial": "1", "sm": "2", "lg": "3"},
            spacing="3",
            width="100%",
        ),
    )


def render_trail(item: rx.Var[dict]) -> rx.Component:
    return rx.box(
        rx.flex(
            rx.box(
                style={
                    "width": "10px",
                    "height": "10px",
                    "background": item["color"],
                    "flex_shrink": "0",
                    "margin_top": "8px",
                }
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(item["layer"], size="1", style={**MONO, "color": t.MUTED}),
                    rx.badge(
                        item["result"],
                        style={
                            "background": item["color"],
                            "color": t.BLACK,
                            "border_radius": "0",
                            "white_space": "nowrap",
                        },
                    ),
                    align="center",
                    spacing="2",
                    wrap="wrap",
                ),
                muted(item["detail"], size="2"),
                spacing="1",
                align="start",
                style={"min_width": "0"},
            ),
            align="start",
            gap="3",
        ),
        style={
            "background": t.CARD_2,
            "border": f"1px solid {t.LINE}",
            "border_radius": "0",
            "padding": "10px 12px",
            "width": "100%",
        },
    )


def trail_card() -> rx.Component:
    return card(
        card_title("route", "Jejak keputusan"),
        muted(
            "Lapisan diperiksa berurutan dari atas. Skor model ditampilkan apa adanya, "
            "dan SUSPICIOUS berarti model tidak dapat memastikan.",
            style={"margin_top": "6px", "margin_bottom": "14px"},
        ),
        rx.vstack(rx.foreach(State.trail, render_trail), spacing="2", width="100%"),
    )


def results_view() -> rx.Component:
    return rx.vstack(
        rx.grid(
            verdict_card(),
            probability_card(),
            timing_card(),
            columns={"initial": "1", "lg": "3"},
            spacing="4",
            width="100%",
        ),
        trail_card(),
        features_card(),
        spacing="4",
        width="100%",
    )


def hero() -> rx.Component:
    return rx.heading(
        "Take your link back",
        as_="h1",
        style={
            "font_family": t.DISPLAY_FONT,
            "text_transform": "uppercase",
            "font_size": "clamp(2.6rem, 8vw, 5.6rem)",
            "line_height": "0.95",
            "color": t.WHITE,
            "text_shadow": f"6px 6px 0 {t.BLACK}",
            "transform": "rotate(-3deg)",
            "transform_origin": "left",
            "margin": "8px 0 28px",
        },
    )


def index() -> rx.Component:
    return page_shell(
        hero(),
        rx.vstack(
            search_card(),
            rx.cond(State.error != "", error_callout()),
            rx.cond(State.has_result, results_view(), empty_state()),
            spacing="4",
            width="100%",
            align="stretch",
        ),
        active="cek",
        subtitle="Deteksi phishing dari teks URL",
    )
