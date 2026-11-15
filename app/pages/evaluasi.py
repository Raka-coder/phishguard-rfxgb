"""Halaman evaluasi: ringkasan training (CV) dan laporan hasil_evaluasi.md."""

import json
from pathlib import Path

import reflex as rx

from app.style import ERROR_COLOR, LINK_COLOR

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "docs" / "metrics.json"
HASIL_PATH = ROOT / "docs" / "hasil_evaluasi.md"


class EvalState(rx.State):
    """Muat artefak saat halaman dikunjungi (bukan saat compile)."""

    artefak_ok: bool = False
    trained_at: str = ""
    n_train: str = ""
    n_test: str = ""
    best_a: str = ""
    best_b: str = ""
    cv_data: list[list[str]] = []
    hasil_md: str = ""

    @rx.event
    async def load_artifacts(self):
        try:
            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            hasil = HASIL_PATH.read_text(encoding="utf-8") if HASIL_PATH.exists() else ""
        except Exception:
            self.artefak_ok = False
            self.cv_data = []
            self.hasil_md = ""
            return

        self.artefak_ok = True
        self.trained_at = str(metrics.get("trained_at", ""))
        split = metrics.get("split", {}) or {}
        self.n_train = str(split.get("n_train", ""))
        self.n_test = str(split.get("n_test", ""))
        self.best_a = str(metrics.get("model_a", {}).get("best", ""))
        self.best_b = str(metrics.get("model_b", {}).get("best", ""))

        rows: list[list[str]] = []
        for group, label in (("model_a", "Model A (full)"), ("model_b", "Model B (URL-only)")):
            data = metrics.get(group, {}) or {}
            for model in ("lr", "rf", "xgb"):
                info = data.get(model, {}) or {}
                rows.append(
                    [
                        label,
                        model.upper(),
                        f"{float(info.get('cv_f1_phishing_mean', 0.0)):.4f}",
                        "★" if model == data.get("best") else "",
                    ]
                )
        self.cv_data = rows
        self.hasil_md = hasil


def cv_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Model"),
                rx.table.column_header_cell("Algoritma"),
                rx.table.column_header_cell("CV F1 (phishing)"),
                rx.table.column_header_cell("Terbaik"),
            )
        ),
        rx.table.body(
            rx.foreach(
                EvalState.cv_data,
                lambda row: rx.table.row(
                    rx.table.cell(row[0]),
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[3]),
                ),
            )
        ),
        width="100%",
    )


def evaluasi() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.link("← Kembali ke cek URL", href="/", color=LINK_COLOR),
            rx.heading("Evaluasi Model", size="8"),
            rx.cond(
                EvalState.artefak_ok,
                rx.vstack(
                    rx.text(
                        f"Model A terbaik: {EvalState.best_a} · Model B terbaik: {EvalState.best_b}",
                        size="3",
                    ),
                    rx.text(
                        f"Split: train {EvalState.n_train}, test {EvalState.n_test}, seed 42 (stratified)",
                        size="2",
                    ),
                    rx.text(f"trained_at: {EvalState.trained_at}", size="1"),
                    rx.card(
                        rx.vstack(
                            rx.text("Ringkasan training (5-fold CV, F1 phishing)", weight="bold"),
                            cv_table(),
                            width="100%",
                            spacing="2",
                        ),
                        width="100%",
                    ),
                    rx.card(
                        rx.vstack(
                            rx.text("Hasil evaluasi test set (docs/hasil_evaluasi.md)", weight="bold"),
                            rx.box(
                                rx.markdown(EvalState.hasil_md),
                                overflow_x="auto",
                                width="100%",
                            ),
                            width="100%",
                            spacing="2",
                        ),
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                    max_width="960px",
                ),
                rx.text(
                    "Artefak belum ada. Jalankan `uv run python src/train.py` dan `uv run python src/evaluate.py` dulu.",
                    color=ERROR_COLOR,
                ),
            ),
            spacing="4",
            width="100%",
            max_width="960px",
            align="stretch",
        ),
        padding="2rem",
    )
