"""Entry point aplikasi Reflex PhishGuard."""

import reflex as rx

from app.pages.index import index

app = rx.App()
app.add_page(index, route="/", title="PhishGuard")
