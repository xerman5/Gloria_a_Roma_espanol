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

Output is grouped one folder per card type with fronts + explicit `_back` files and a readme; folder names, the shared order-back name and the readme are localized in `deck.PACKAGING` (en/es, fallback en) — the one place in code that lists languages, because it is packaging text, not card data. File names carry the copy count: `Academy_es(3x).png`. Merchant bonus and leader backs are duplicates of the front by design. Every PNG goes through `deck.png_bytes`: flattened onto white, RGB (no alpha), 300 dpi, sRGB ICC embedded — print shops reject alpha and untagged files, so don't save images any other way. Deck selection, naming and batch rendering live in `gtr/deck.py` and are shared by the CLI and `app.py` — change them there, not in either front-end. Headless UI check: `streamlit.testing.v1.AppTest.from_file("app.py").run()`.

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
- Artwork is vector: `load_png` rasterizes `<image>.svg` with `cairosvg` at the exact target width (needs libcairo — `packages.txt` for Streamlit Cloud, a venv locally). All 81 assets are SVG; the earlier 4x PNGs are in git history. `load_png` still falls back to `<image>.png` if no SVG exists. Traced SVGs carry the suit colour slightly off, so `_snap_fill_to_suit` replaces the one fill closest to `suit.color` (≤ `SUIT_COLOR_TOLERANCE` per channel) before rasterizing; secondary colours (water, shadows, gold) are left alone. Pass `suit_color=` for card art, role icons and material icons; not for influence coins.
- Card artwork is pasted exactly as authored on its own canvas (full card width), optionally nudged by `cards.csv` `image_offset` (fraction of card width). Do **not** auto-center on the content bounding box or centroid: both were tried and clipped wide asymmetric illustrations (Forum Romanum's obelisk, Stairway, Road) — the illustrator already centred the visual axis on the canvas.
- `ImageDraw` ignores alpha on RGBA canvases; anything translucent (text backdrops, halos) must go through `draw_translucent`.
- Text markup: `|word` is a line-break *hint*, `||` a hard paragraph break. `_group_by_line` honors the hints only if every hinted line of the paragraph fits; otherwise it re-wraps the whole paragraph, so English-tuned breaks don't strand words in longer languages. Titles (`header_fragments`) flow like body text — uppercase, tracked, a real space between words, wrapping only when a line is full — not one word per line as in the .NET original. Bold is rule-based (`BOLD_WORD`: ALL-CAPS words, `x2`, `+N`); words containing a role or material name (in the active language) are also colored by suit.
