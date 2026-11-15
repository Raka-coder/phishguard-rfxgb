"""API PhishGuard: POST /check dan GET /health (FastAPI, port 8001)."""

from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.predict import _load, predict_url

ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

app = FastAPI(title="PhishGuard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


class CheckRequest(BaseModel):
    url: str


class TopFeature(BaseModel):
    feature: str
    value: float
    impact: str


class CheckResponse(BaseModel):
    url: str
    label: int
    label_name: str
    verdict: str
    probability: float | None
    inference_ms: float
    top_features: list[TopFeature]
    decision_source: str
    reason: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Body tanpa field `url` (atau tipe salah) -> 400, bukan 422."""
    return JSONResponse(
        status_code=400,
        content={"detail": "URL tidak valid: body harus berisi field 'url' (string)"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError dari predict_url (kosong/scheme/host) -> 400 dengan pesan aslinya."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/check", response_model=CheckResponse)
def check(body: CheckRequest) -> dict:
    """Prediksi satu URL; endpoint sync karena predict_url CPU-bound (threadpool)."""
    return predict_url(body.url)


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    try:
        _load()
        loaded = True
    except Exception:
        loaded = False
    return {"status": "ok", "model_loaded": loaded}
