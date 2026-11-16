"""Vignettes des cartes de l'accueil : capture le haut de chaque e-mail archivé
dans docs/<id>/thumb.jpg. Ne refait que les vignettes manquantes.

    pip install playwright && python make_thumbs.py

Utilise le Chrome déjà installé (présent sur les runners GitHub) : pas de
`playwright install`. Étape facultative : sans vignette, la carte s'affiche sans image.
"""
import os
import sys

from playwright.sync_api import sync_playwright

DOCS = "docs"


def main():
    todo = [d for d in sorted(os.listdir(DOCS))
            if os.path.isfile(os.path.join(DOCS, d, "metadata.json"))
            and not os.path.exists(os.path.join(DOCS, d, "thumb.jpg"))]
    if not todo:
        return 0
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for d in todo:
            try:
                page.goto("file://" + os.path.abspath(os.path.join(DOCS, d, "index.html")))
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass  # une image distante lente ne doit pas bloquer la capture
                page.locator("#emailFrame").screenshot(
                    path=os.path.join(DOCS, d, "thumb.jpg"), type="jpeg", quality=70)
                print("ok", d)
            except Exception as e:  # une vignette ratée ne bloque pas les autres
                failed += 1
                print("échec", d, e, file=sys.stderr)
        browser.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
