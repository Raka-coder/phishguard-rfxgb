"""Halaman index: input URL, tombol Periksa, dan kartu hasil."""

import reflex as rx

from app.app_state import State


def render_feature(item: rx.Var[dict]) -> rx.Component:
    return rx.hstack(
        rx.text(item["feature"], size="2", weight="bold"),
        rx.text("=", size="2"),
        rx.text(item["value"], size="2"),
        rx.spacer(),
        rx.text(item["impact"], size="2"),
        width="100%",
    )


def result_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(State.label_name, size="6", weight="bold", color=State.verdict_color),
            rx.text("Probabilitas phishing: ", State.probability_pct),
            rx.text("Waktu inference: ", State.inference_ms, " ms"),
            rx.divider(),
            rx.text("Top-5 fitur", size="3", weight="bold"),
            rx.foreach(State.top_features, render_feature),
            spacing="2",
            width="100%",
        ),
        width="100%",
    )


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("PhishGuard", size="9"),
            rx.text(
                "Deteksi phishing dari string URL — tanpa membuka atau memindai situs.",
                size="3",
            ),
            rx.form.root(
                rx.hstack(
                    rx.input(
                        value=State.url,
                        on_change=State.set_url,
                        placeholder="https://contoh.com/login",
                        width="100%",
                    ),
                    rx.button(
                        "Periksa",
                        type="submit",
                        loading=State.loading,
                        disabled=State.loading,
                    ),
                    width="100%",
                    spacing="2",
                ),
                on_submit=State.check_url,
                reset_on_submit=False,
                width="100%",
            ),
            rx.cond(
                State.loading,
                rx.hstack(rx.spinner(size="2"), rx.text("Memeriksa...", size="2")),
                rx.fragment(),
            ),
            rx.cond(
                State.error != "",
                rx.text(State.error, color="red", size="2"),
                rx.fragment(),
            ),
            rx.cond(State.has_result, result_card(), rx.fragment()),
            spacing="4",
            width="100%",
            max_width="720px",
            align="stretch",
        ),
        padding="2rem",
    )
