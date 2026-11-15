"""Entry point aplikasi Reflex PhishGuard."""

import reflex as rx

from app.pages.evaluasi import EvalState, evaluasi
from app.pages.index import index
from app.style import APP_STYLE, STYLESHEETS, THEME

app = rx.App(theme=THEME, style=APP_STYLE, stylesheets=STYLESHEETS)
app.add_page(index, route="/", title="PhishGuard")
app.add_page(evaluasi, route="/evaluasi", title="Evaluasi — PhishGuard", on_load=EvalState.load_artifacts)
