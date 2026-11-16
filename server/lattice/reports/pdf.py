"""Headless PDF capture of exported report HTML (DR-9: one rendering path).

The stored HTML version is loaded in headless Chromium and printed; the same
document a reviewer saw in the browser is what the PDF freezes. Figures and
math load from CDNs, so offline capture degrades to text (stated, not hidden).
"""

from fastapi import HTTPException


def render_pdf(html: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise HTTPException(
            503,
            "PDF export needs Playwright: pip install playwright && playwright install chromium",
        )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content(html, wait_until="networkidle")
                # Give Plotly/KaTeX a beat to paint after their CDN scripts settle.
                page.wait_for_timeout(1200)
                return page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "18mm", "bottom": "18mm", "left": "15mm", "right": "15mm"},
                )
            finally:
                browser.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"PDF rendering failed: {type(exc).__name__}: {exc}")
