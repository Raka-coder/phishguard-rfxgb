"""State halaman index: panggil API /check dan simpan hasil yang sudah di-flatten."""

import os

import httpx
import reflex as rx

from app import style as t

API_URL = os.getenv("PHISHGUARD_API_URL", "http://localhost:8001/check")

# Client module-level: import httpcore/ssl terjadi saat startup, bukan di request pertama
# (menghindari event loop terblokir ~1 detik pada klik pertama), sekaligus reuse koneksi.
_CLIENT = httpx.AsyncClient(timeout=10.0)

# Nama fitur dataset -> label yang bisa dibaca orang awam.
FEATURE_LABELS = {
    "URLLength": "Panjang URL",
    "DomainLength": "Panjang domain",
    "TLDLength": "Panjang akhiran domain (TLD)",
    "NoOfSubDomain": "Jumlah subdomain",
    "IsDomainIP": "Domain berupa alamat IP",
    "IsHTTPS": "Memakai HTTPS",
    "NoOfLettersInURL": "Jumlah huruf",
    "LetterRatioInURL": "Rasio huruf",
    "NoOfDegitsInURL": "Jumlah angka",
    "DegitRatioInURL": "Rasio angka",
    "NoOfEqualsInURL": "Jumlah tanda =",
    "NoOfQMarkInURL": "Jumlah tanda ?",
    "NoOfAmpersandInURL": "Jumlah tanda &",
    "NoOfOtherSpecialCharsInURL": "Jumlah karakter khusus",
    "SpacialCharRatioInURL": "Rasio karakter khusus",
    "HasObfuscation": "Ada penyamaran karakter",
    "NoOfObfuscatedChar": "Jumlah karakter tersamar",
    "ObfuscationRatio": "Rasio karakter tersamar",
    "TLDLegitimateProb": "Skor reputasi TLD",
}
BOOL_FEATURES = {"IsDomainIP", "IsHTTPS", "HasObfuscation"}
IMPACT_DIR = {"meningkatkan risiko": "up", "menurunkan risiko": "down"}

# Warna baris trail menurut hasil lapisan (ikon dinamis tidak didukung Reflex 0.11).
TRAIL_COLORS = {
    "tinggi": t.RED,
    "sedang": t.YELLOW,
    "rendah": t.GREEN,
    "cocok": t.GREEN,
    "tidak cocok": t.MUTED,
    "dilewati": t.MUTED,
    "tidak tersedia": t.MUTED,
}
RISK_LABELS = {"tinggi": "Risiko tinggi", "sedang": "Risiko sedang", "rendah": "Risiko rendah"}
DISPLAY_LABELS = {"SUSPICIOUS": "TIDAK TERVERIFIKASI"}


def display_verdict_label(label_name: str) -> str:
    """Label user-facing netral; field API label_name tidak diubah."""
    name = str(label_name or "")
    return DISPLAY_LABELS.get(name, name)


def build_trail_rows(items: list[dict]) -> list[dict]:
    """Ubah trail API menjadi baris tampilan (warna status ditentukan di server)."""
    rows = []
    for item in items or []:
        result = str(item.get("result", ""))
        rows.append(
            {
                "layer": str(item.get("layer", "")),
                "result": result,
                "detail": str(item.get("detail", "")),
                "color": TRAIL_COLORS.get(result, t.MUTED),
            }
        )
    return rows


def build_feature_rows(items: list[dict]) -> list[dict]:
    """Ubah top_features API menjadi baris tampilan (label, nilai teks, arah dampak)."""
    rows = []
    for item in items or []:
        name = str(item.get("feature", ""))
        value = float(item.get("value") or 0.0)
        impact = str(item.get("impact", ""))
        if name in BOOL_FEATURES:
            shown = "Ya" if value >= 0.5 else "Tidak"
        else:
            shown = f"{value:.3g}"
        rows.append(
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": shown,
                "impact": impact,
                "dir": IMPACT_DIR.get(impact, "flat"),
            }
        )
    return rows


class State(rx.State):
    """Input URL, status request, dan hasil prediksi (semua bertipe, tanpa dict mentah)."""

    url: str = ""
    loading: bool = False
    error: str = ""
    has_result: bool = False
    submitted_url: str = ""
    label_name: str = ""
    verdict: str = ""
    risk_level: str = ""
    probability_pct: str = ""
    bar_width: str = "0%"
    prob_data: list[dict] = []
    inference_ms: str = ""
    top_features: list[dict] = []
    decision_source: str = ""
    reason: str = ""
    trail: list[dict] = []

    @rx.var
    def risk_label(self) -> str:
        return RISK_LABELS.get(self.risk_level, "")

    @rx.var
    def risk_color(self) -> str:
        return {"tinggi": t.RED, "sedang": t.YELLOW, "rendah": t.GREEN}.get(self.risk_level, t.MUTED)

    @rx.var
    def display_label(self) -> str:
        return display_verdict_label(self.label_name)

    @rx.var
    def verdict_note(self) -> str:
        if self.label_name == "SUSPICIOUS":
            return "Model tidak dapat memastikan apakah URL ini aman atau phishing, jadi periksa sendiri sebelum membuka atau memasukkan data."
        return self.reason

    @rx.var
    def is_phishing(self) -> bool:
        return self.label_name == "PHISHING"

    @rx.var
    def verdict_color(self) -> str:
        if self.label_name == "PHISHING":
            return t.RED
        if self.label_name == "SUSPICIOUS":
            return t.MUTED
        return t.GREEN

    @rx.event
    def set_url(self, value: str):
        self.url = value

    @rx.event
    def use_example(self, value: str):
        """Isi input dengan URL contoh lalu langsung periksa."""
        self.url = value
        return State.check_url

    @rx.event
    async def check_url(self):
        """POST ke API; Enter di input dan klik tombol sama-sama memicu form submit."""
        target = self.url.strip()
        self.error = ""
        self.has_result = False
        if not target:
            self.error = "URL tidak boleh kosong. Tempel alamat lengkap, misalnya https://contoh.com/login."
            return

        self.loading = True
        yield
        try:
            response = await _CLIENT.post(API_URL, json={"url": target})
            if response.status_code == 400:
                self.error = str(response.json().get("detail", "URL tidak valid."))
                return
            if response.status_code != 200:
                self.error = f"API mengembalikan status {response.status_code}."
                return
            body = response.json()
        except httpx.HTTPError:
            self.error = (
                f"Tidak dapat menghubungi API di {API_URL}. "
                "Jalankan `uv run uvicorn api.main:app --port 8001` dulu."
            )
        except ValueError:
            self.error = "Respons API tidak dapat dibaca."
        else:
            probability_raw = body.get("probability")
            self.submitted_url = target
            self.label_name = str(body.get("label_name", ""))
            self.verdict = str(body.get("verdict", ""))
            self.risk_level = str(body.get("risk_level", ""))
            self.decision_source = str(body.get("decision_source", ""))
            self.reason = str(body.get("reason", ""))
            self.trail = build_trail_rows(body.get("trail") or [])
            if probability_raw is None:
                self.probability_pct = "—"
                self.bar_width = "0%"
                self.prob_data = []
            else:
                probability = float(probability_raw)
                self.probability_pct = f"{probability * 100:.2f}%"
                self.bar_width = f"{min(max(probability, 0.0), 1.0) * 100:.2f}%"
                self.prob_data = [
                    {"name": "Phishing", "value": round(probability * 100, 2), "fill": t.RED},
                    {"name": "Legit", "value": round(100 - probability * 100, 2), "fill": t.GREEN},
                ]
            self.inference_ms = f"{float(body.get('inference_ms') or 0.0):.2f}"
            self.top_features = build_feature_rows(body.get("top_features") or [])
            self.has_result = True
        finally:
            self.loading = False
