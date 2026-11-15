"""Halaman evaluasi: ringkasan training (CV), grafik, confusion matrix, dan laporan test set."""

import json
import re
from pathlib import Path

import reflex as rx

from app import style as t
from app.components import card, card_title, muted, page_shell

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "docs" / "metrics.json"
HASIL_PATH = ROOT / "docs" / "hasil_evaluasi.md"

MODEL_GROUPS = (("model_a", "Model A (full)"), ("model_b", "Model B (URL-only)"))
ALGOS = ("lr", "rf", "xgb")
_CONF_RE = re.compile(r"Confusion matrix — Model B.*?TP=(\d+), FN=(\d+), FP=(\d+), TN=(\d+)", re.S)


# --- Helper murni (mudah dites tanpa Reflex) --------------------------------
def build_cv_rows(metrics: dict) -> list[list[str]]:
    """Baris tabel CV: [grup, algoritma, F1, penanda terbaik]."""
    rows: list[list[str]] = []
    for group, label in MODEL_GROUPS:
        data = metrics.get(group, {}) or {}
        for model in ALGOS:
            info = data.get(model, {}) or {}
            rows.append(
                [
                    label,
                    model.upper(),
                    f"{float(info.get('cv_f1_phishing_mean', 0.0)):.4f}",
                    "★" if model == data.get("best") else "",
                ]
            )
    return rows


def build_cv_chart(metrics: dict) -> list[dict]:
    """Satu baris per algoritma: F1 rata-rata CV untuk Model A dan Model B."""
    out = []
    for model in ALGOS:
        row = {"model": model.upper()}
        for group, label in (("model_a", "Model A"), ("model_b", "Model B")):
            info = (metrics.get(group, {}) or {}).get(model, {}) or {}
            row[label] = round(float(info.get("cv_f1_phishing_mean", 0.0)), 4)
        out.append(row)
    return out


def build_fold_chart(metrics: dict) -> list[dict]:
    """F1 per fold untuk Model B (satu baris per fold, satu kolom per algoritma)."""
    group = metrics.get("model_b", {}) or {}
    folds = {m: (group.get(m, {}) or {}).get("cv_folds", []) for m in ALGOS}
    n = max((len(v) for v in folds.values()), default=0)
    out = []
    for i in range(n):
        row = {"fold": f"Fold {i + 1}"}
        for m in ALGOS:
            row[m.upper()] = round(float(folds[m][i]), 4) if i < len(folds[m]) else None
        out.append(row)
    return out


def build_split_chart(split: dict) -> list[dict]:
    return [
        {"name": "Data latih", "value": int(split.get("n_train") or 0), "fill": t.PURPLE},
        {"name": "Data uji", "value": int(split.get("n_test") or 0), "fill": t.ORANGE},
    ]


def parse_confusion(markdown: str) -> dict[str, str] | None:
    """TP/FN/FP/TN Model B dari hasil_evaluasi.md; None bila format tidak cocok."""
    match = _CONF_RE.search(markdown or "")
    if not match:
        return None
    return {k: format_count(v) for k, v in zip(("tp", "fn", "fp", "tn"), match.groups())}


def format_count(value) -> str:
    """188636 -> '188.636' (pemisah ribuan gaya Indonesia); non-angka dikembalikan apa adanya."""
    if value in (None, ""):
        return ""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def clean_report(markdown: str) -> str:
    """Sel tabel memakai <br>; renderer markdown menampilkannya sebagai teks, jadi ganti."""
    return markdown.replace("<br>", "; ")


# --- State ------------------------------------------------------------------
class EvalState(rx.State):
    """Muat artefak saat halaman dikunjungi (bukan saat compile)."""

    artefak_ok: bool = False
    trained_at: str = ""
    n_train: str = ""
    n_test: str = ""
    n_features_b: str = ""
    best_a: str = ""
    best_b: str = ""
    cv_data: list[list[str]] = []
    cv_chart: list[dict] = []
    fold_chart: list[dict] = []
    split_chart: list[dict] = []
    has_conf: bool = False
    conf_tp: str = ""
    conf_fn: str = ""
    conf_fp: str = ""
    conf_tn: str = ""
    hasil_md: str = ""

    @rx.var
    def trained_date(self) -> str:
        return self.trained_at[:10]

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
        self.n_train = format_count(split.get("n_train", ""))
        self.n_test = format_count(split.get("n_test", ""))
        self.n_features_b = str((metrics.get("model_b", {}) or {}).get("n_features", ""))
        self.best_a = str(metrics.get("model_a", {}).get("best", ""))
        self.best_b = str(metrics.get("model_b", {}).get("best", ""))
        self.cv_data = build_cv_rows(metrics)
        self.cv_chart = build_cv_chart(metrics)
        self.fold_chart = build_fold_chart(metrics)
        self.split_chart = build_split_chart(split)

        conf = parse_confusion(hasil)
        self.has_conf = conf is not None
        if conf:
            self.conf_tp, self.conf_fn, self.conf_fp, self.conf_tn = (conf[k] for k in ("tp", "fn", "fp", "tn"))
        self.hasil_md = clean_report(hasil)


# --- Komponen ---------------------------------------------------------------
def stat_card(value, label: str) -> rx.Component:
    return card(
        rx.hstack(
            rx.text(
                value,
                style={"font_size": "1.9rem", "font_weight": "700", "line_height": "1", "text_transform": "uppercase"},
            ),
            muted(label),
            align="end",
            spacing="3",
            wrap="wrap",
        ),
        padding="18px 20px",
    )


GRID = {"stroke": "#444444", "stroke_dasharray": "6 6"}
TOOLTIP_STYLE = {
    "background": t.BLACK,
    "border": f"3px solid {t.WHITE}",
    "border_radius": "0",
    "color": t.TEXT,
}


def cv_bar_chart() -> rx.Component:
    return card(
        card_title("chart-bar", "F1 phishing per model"),
        muted(
            "Rata-rata 5-fold CV. Sumbu dipotong di 0,98–1,00 supaya selisihnya terlihat.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.bar(data_key="Model A", fill=t.ORANGE),
            rx.recharts.bar(data_key="Model B", fill=t.PURPLE),
            rx.recharts.x_axis(data_key="model", stroke=t.MUTED),
            rx.recharts.y_axis(domain=[0.98, 1], stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.cv_chart,
            width="100%",
            height=260,
        ),
    )


def fold_line_chart() -> rx.Component:
    return card(
        card_title("activity", "Stabilitas per fold (Model B)"),
        muted(
            "F1 phishing di tiap fold. Garis yang datar berarti model konsisten.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.line_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.line(data_key="LR", stroke=t.YELLOW, type_="monotone", dot=False),
            rx.recharts.line(data_key="RF", stroke=t.ORANGE, type_="monotone", dot=False),
            rx.recharts.line(data_key="XGB", stroke=t.PURPLE_LIGHT, type_="monotone", dot=False),
            rx.recharts.x_axis(data_key="fold", stroke=t.MUTED),
            rx.recharts.y_axis(domain=[0.985, 1], stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.fold_chart,
            width="100%",
            height=260,
        ),
    )


def _conf_cell(value, caption: str, good: bool) -> rx.Component:
    """Benar (TP/TN) = putih; salah (FN/FP) = merah."""
    fg = t.BLACK if good else t.WHITE
    return rx.box(
        rx.text(value, style={"font_size": "1.6rem", "font_weight": "700", "line_height": "1.1", "color": fg}),
        muted(caption, size="1", style={"color": fg}),
        style={
            "background": t.WHITE if good else t.P5_RED,
            "border": f"3px solid {t.WHITE if good else t.P5_RED}",
            "border_radius": "0",
            "padding": "14px",
        },
    )


def _conf_axis(text: str) -> rx.Component:
    return rx.flex(muted(text, size="1"), align="center", justify="center", style={"padding": "4px"})


def confusion_card() -> rx.Component:
    return card(
        card_title("layers", "Confusion matrix (Model B)"),
        muted(
            "Hasil pada data uji, ambang 50%. Putih = prediksi benar, merah = salah.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "14px"},
        ),
        rx.cond(
            EvalState.has_conf,
            rx.grid(
                rx.box(),
                _conf_axis("Prediksi phishing"),
                _conf_axis("Prediksi legit"),
                _conf_axis("Aktual phishing"),
                _conf_cell(EvalState.conf_tp, "Terdeteksi (TP)", True),
                _conf_cell(EvalState.conf_fn, "Lolos (FN)", False),
                _conf_axis("Aktual legit"),
                _conf_cell(EvalState.conf_fp, "Salah tandai (FP)", False),
                _conf_cell(EvalState.conf_tn, "Benar legit (TN)", True),
                columns="110px 1fr 1fr",
                spacing="2",
                width="100%",
            ),
            muted("Jalankan `uv run python src/evaluate.py` untuk membuat laporan test set."),
        ),
    )


def split_card() -> rx.Component:
    return card(
        card_title("database", "Pembagian data"),
        muted(
            "Stratified 80/20, seed 42. Data uji tidak dipakai saat training.",
            size="1",
            style={"margin_top": "6px"},
        ),
        rx.box(
            rx.recharts.pie_chart(
                rx.recharts.pie(
                    data=EvalState.split_chart,
                    data_key="value",
                    name_key="name",
                    inner_radius=58,
                    outer_radius=80,
                    stroke="none",
                ),
                rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
                width="100%",
                height=200,
            ),
            rx.flex(
                rx.text("80 / 20", style={"font_size": "1.3rem", "font_weight": "700"}),
                direction="column",
                align="center",
                justify="center",
                style={"position": "absolute", "inset": "0", "pointer_events": "none"},
            ),
            style={"position": "relative", "width": "100%", "margin_top": "6px"},
        ),
        rx.hstack(
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.PURPLE}),
                muted("Latih", size="1"),
                align="center",
                spacing="1",
            ),
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.ORANGE}),
                muted("Uji", size="1"),
                align="center",
                spacing="1",
            ),
            justify="center",
            width="100%",
        ),
    )


def _head(text: str, align: str = "left") -> rx.Component:
    return rx.table.column_header_cell(
        text,
        style={"background": t.PURPLE_DEEP, "color": t.TEXT, "text_align": align, "font_weight": "600"},
    )


def cv_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _head("Model"),
                _head("Algoritma"),
                _head("F1 phishing (rata-rata CV)", "right"),
                _head("Terbaik", "center"),
            )
        ),
        rx.table.body(
            rx.foreach(
                EvalState.cv_data,
                lambda row: rx.table.row(
                    rx.table.cell(row[0]),
                    rx.table.cell(row[1], style={"font_weight": "600"}),
                    rx.table.cell(
                        row[2],
                        style={"text_align": "right", "font_variant_numeric": "tabular-nums"},
                    ),
                    rx.table.cell(
                        rx.cond(
                            row[3] != "",
                            rx.box(
                                "Terbaik",
                                style={
                                    "display": "inline-block",
                                    "background": t.GRADIENT,
                                    "color": t.WHITE,
                                    "font_size": "0.75rem",
                                    "font_weight": "700",
                                    "padding": "2px 10px",
                                    "border_radius": "0",
                                },
                            ),
                            "",
                        ),
                        style={"text_align": "center"},
                    ),
                    style={"background": rx.cond(row[3] != "", "rgba(230,0,18,0.18)", "transparent")},
                ),
            )
        ),
        width="100%",
        variant="ghost",
    )


REPORT_STYLE = {
    "color": t.TEXT,
    "font_size": "0.92rem",
    "line_height": "1.6",
    "overflow_x": "auto",
    "width": "100%",
    "& h1": {"font_size": "1.4rem", "margin": "0 0 0.75rem"},
    "& h2": {
        "font_size": "1.15rem",
        "margin": "1.6rem 0 0.5rem",
        "padding_left": "0.6rem",
        "border_left": f"4px solid {t.PURPLE}",
    },
    "& h3": {"font_size": "1rem", "margin": "1.2rem 0 0.4rem", "color": t.PURPLE_LIGHT},
    "& table": {"width": "100%", "border_collapse": "collapse", "margin": "0.6rem 0", "font_size": "0.85rem"},
    "& th": {
        "background": t.PURPLE_DEEP,
        "color": t.TEXT,
        "text_align": "left",
        "padding": "0.45rem 0.7rem",
        "white_space": "nowrap",
    },
    "& td": {"padding": "0.45rem 0.7rem", "border_bottom": f"1px solid {t.LINE}", "vertical_align": "top"},
    "& code": {
        "background": t.CARD_2,
        "padding": "0.05rem 0.35rem",
        "border_radius": "0",
        "word_break": "break-all",
        "font_size": "0.85em",
    },
    "& ul": {"padding_left": "1.2rem", "margin": "0.4rem 0"},
}


def report_card() -> rx.Component:
    return card(
        rx.accordion.root(
            rx.accordion.item(
                header="Laporan lengkap test set: metrik, confusion matrix, contoh FP dan FN",
                content=rx.box(rx.markdown(EvalState.hasil_md), style=REPORT_STYLE),
                value="laporan",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
        padding="6px 12px",
    )


def loaded_view() -> rx.Component:
    return rx.vstack(
        rx.callout(
            "Metrik di halaman ini adalah metrik model-only pada test set PhiUSIIL. "
            "Lapisan reputasi offline (allowlist) menurunkan false positive dunia nyata "
            "tanpa mengubah test set; lihat hasil cek URL di halaman utama.",
            icon="info",
            color_scheme="blue",
            style={"width": "100%"},
        ),
        rx.grid(
            stat_card(EvalState.best_b, "Model di aplikasi"),
            stat_card(EvalState.n_features_b, "Fitur Model B"),
            stat_card(EvalState.n_train, "Data latih"),
            stat_card(EvalState.n_test, "Data uji"),
            columns={"initial": "1", "sm": "2", "lg": "4"},
            spacing="3",
            width="100%",
        ),
        rx.grid(
            cv_bar_chart(),
            fold_line_chart(),
            columns={"initial": "1", "lg": "2"},
            spacing="4",
            width="100%",
        ),
        rx.grid(
            confusion_card(),
            split_card(),
            columns={"initial": "1", "lg": "2"},
            spacing="4",
            width="100%",
        ),
        card(
            card_title("layers", "Ringkasan validasi silang"),
            muted(
                "5-fold CV pada data latih. Model terbaik dipilih dari rata-rata F1 kelas phishing.",
                size="1",
                style={"margin_top": "6px", "margin_bottom": "12px"},
            ),
            cv_table(),
        ),
        report_card(),
        rx.hstack(
            muted("Dilatih pada", size="1"),
            muted(EvalState.trained_date, size="1"),
            spacing="1",
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


def missing_view() -> rx.Component:
    return rx.callout(
        "Artefak belum ada. Jalankan `uv run python src/train.py` dan "
        "`uv run python src/evaluate.py` dulu.",
        icon="triangle-alert",
        color_scheme="red",
        style={"width": "100%"},
    )


def evaluasi() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.vstack(
                rx.heading(
                    "Evaluasi model",
                    as_="h1",
                    style={
                        "font_family": t.DISPLAY_FONT,
                        "text_transform": "uppercase",
                        "font_weight": "400",
                        "font_size": "clamp(2rem, 5vw, 3.2rem)",
                        "line_height": "0.95",
                        "color": t.WHITE,
                        "text_shadow": f"6px 6px 0 {t.BLACK}",
                        "transform": "rotate(-3deg)",
                        "transform_origin": "left",
                        "margin": "8px 0 20px",
                    },
                ),
                muted("Seberapa akurat PhishGuard membedakan URL phishing dari URL legit.", size="3"),
                spacing="1",
                align="start",
            ),
            rx.cond(EvalState.artefak_ok, loaded_view(), missing_view()),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        active="evaluasi",
        subtitle="Hasil training dan pengujian",
    )
