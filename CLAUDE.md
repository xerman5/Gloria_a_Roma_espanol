# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python/Pillow generator of print-ready card images (300 dpi, with bleed) for the board game *Glory to Rome*, with multi-language text. It replaced an earlier .NET/System.Drawing implementation (deleted; see git history before this rewrite for the original 3×6 page composer, which is not ported yet).

## Commands

```bash
pip install -r requirements.txt               # Pillow + Streamlit
streamlit run app.py                          # web UI (also what Streamlit Community Cloud runs)
python3 render_card.py --list                 # deck contents + copy counts (must total 244)
python3 render_card.py Academy --lang es      # one or more card keys
python3 render_card.py --all --lang en        # every card face + the shared order-card back
python3 render_card.py --all --bleed 2        # bleed in mm (default 3, the common print-shop spec)
python3 render_card.py --all --sets Standard Republic --types order site
```

Output file names carry the copy count: `Academy_es(3x).png`. Deck selection, naming and batch rendering live in `gtr/deck.py` and are shared by the CLI and `app.py` — change them there, not in either front-end. Headless UI check: `streamlit.testing.v1.AppTest.from_file("app.py").run()`.

Output goes to `output/` (gitignored). There is no test suite; validate by rendering and looking at the PNGs.

## Data model — `data/cards.csv` is the single source of truth

One row per distinct card, of every type (`order`, `site`, `merchant_bonus`, `leader`, `jack`), with explicit `copies`. Localized columns are suffixed by language (`title_en`, `title_es`, `text_*`, `back_text_*`); empty cells fall back to `en`. `image`/`back_image` are paths under `assets/images/` without extension. The 10 `Promo` cards are the optional BGG fan-made expansion.

`data/suits.csv` holds the 6 suits: `value` (points = influence = site cost), `color`, icon paths, `role_<lang>`. The material name is deliberately **not** stored there: it is the `title_*` of the suit's site card (`Renderer.material_name`). Don't reintroduce a duplicate.

Adding a language = adding `title_xx`/`text_xx`/`back_text_xx` columns to `cards.csv` and `role_xx` to `suits.csv`. Nothing in code lists languages.

## Rendering conventions (`gtr/render.py`)

- Sizes are in millimetres (`CardSize`: 63.5 × 88.9 poker trim, 3 mm bleed, 1.6 mm safe margin) converted at 300 dpi by `mm_to_px`. All layout is expressed as percentages of the card's usable rectangle (constants at the top), so it scales with any `CardSize`.
- `Renderer(language)` loads data and renders; `Renderer.render(card)` dispatches by `card.type` and returns `[(suffix, image)]`, one per printable face (sites and jacks have two). `order_card_back()` is the shared back.
- Cards are rendered as full-bleed rectangles with square corners: the printer die-cuts the rounding after printing, so never draw rounded corners.
- Diagonal stripes (`draw_stripes`) can be clipped to a region; the site front uses that for its bottom cost strip.
- Card artwork is centered on its non-transparent bounding box (`paste_full_width(center_on_content=True)`), not on the PNG canvas.
- `ImageDraw` ignores alpha on RGBA canvases; anything translucent (text backdrops, halos) must go through `draw_translucent`.
- Text markup: `|word` is a line-break *hint*, `||` a hard paragraph break. `_group_by_line` honors the hints only if every hinted line of the paragraph fits; otherwise it re-wraps the whole paragraph, so English-tuned breaks don't strand words in longer languages. Bold is rule-based (`BOLD_WORD`: ALL-CAPS words, `x2`, `+N`); words containing a role or material name (in the active language) are also colored by suit.
