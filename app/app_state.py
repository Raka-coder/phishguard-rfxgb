"""State halaman index: panggil API /check dan simpan hasil yang sudah di-flatten."""

import os

import httpx
import reflex as rx

API_URL = os.getenv("PHISHGUARD_API_URL", "http://localhost:8001/check")

# Client module-level: import httpcore/ssl terjadi saat startup, bukan di request pertama
# (menghindari event loop terblokir ~1 detik pada klik pertama), sekaligus reuse koneksi.
_CLIENT = httpx.AsyncClient(timeout=10.0)


class State(rx.State):
    """Input URL, status request, dan hasil prediksi (semua bertipe, tanpa dict mentah)."""

    url: str = ""
    loading: bool = False
    error: str = ""
    has_result: bool = False
    label_name: str = ""
    probability_pct: str = ""
    inference_ms: str = ""
    top_features: list[dict] = []

    @rx.var
    def is_phishing(self) -> bool:
        return self.label_name == "PHISHING"

    @rx.var
    def verdict_color(self) -> str:
        return "red" if self.is_phishing else "green"

    @rx.event
    def set_url(self, value: str):
        self.url = value

    @rx.event
    async def check_url(self):
        """POST ke API; Enter di input dan klik tombol sama-sama memicu form submit."""
        target = self.url.strip()
        self.error = ""
        self.has_result = False
        if not target:
            self.error = "URL tidak boleh kosong."
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
            self.label_name = str(body.get("label_name", ""))
            self.probability_pct = f"{float(body.get('probability') or 0.0) * 100:.2f}%"
            self.inference_ms = f"{float(body.get('inference_ms') or 0.0):.2f}"
            self.top_features = [
                {
                    "feature": str(item.get("feature", "")),
                    "value": f"{float(item.get('value') or 0.0):.3g}",
                    "impact": str(item.get("impact", "")),
                }
                for item in (body.get("top_features") or [])
            ]
            self.has_result = True
        finally:
            self.loading = False
