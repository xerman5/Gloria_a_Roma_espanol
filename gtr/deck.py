"""Deck selection, batch rendering and print-ready export shared by the CLI and the web app."""

import io

from PIL import Image, ImageCms

from .data import Card
from .render import DPI, Renderer

SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

CARD_TYPES = ["order", "site", "merchant_bonus", "leader", "jack"]
SETS = ["Standard", "Republic", "Imperium", "Promo"]


def select_cards(cards: dict, sets=None, types=None) -> list:
    """Cards whose set and type are in the given lists (None = no filter). Non-order cards
    belong to every deck, so `sets` only filters order cards."""
    return [
        c for c in cards.values()
        if (types is None or c.type in types)
        and (sets is None or c.type != "order" or c.set in sets)
    ]


# Packaging strings (folder names, readme) per language; card text itself lives in data/cards.csv.
PACKAGING = {
    "en": {
        "folders": {"order": "1 Order cards", "site": "2 Sites", "merchant_bonus": "3 Merchant bonuses",
                    "leader": "4 Leader", "jack": "5 Jack"},
        "order_back": "Order Back",
        "readme_name": "README.txt",
        "readme": """Glory to Rome - print files
Every file name ends with the number of copies to print, e.g. (3x).
Each folder holds the fronts and the matching backs of one card kind:

1 Order cards      one front per card; ALL of them share the single back "Order Back".
2 Sites            two-sided: front = in-town site, back = out-of-town site (striped).
3 Merchant bonuses identical on both sides ("_back" is the same image, printed twice).
4 Leader           identical on both sides.
5 Jack             front = sword, back = quill.

PNG, 300 dpi, RGB with sRGB profile, {bleed} mm bleed on every side, square corners
(round them when die-cutting). Trim size 63.5 x 88.9 mm (poker).
""",
    },
    "es": {
        "folders": {"order": "1 Cartas de orden", "site": "2 Solares", "merchant_bonus": "3 Bonus de comerciante",
                    "leader": "4 Lider", "jack": "5 Senador"},
        "order_back": "Reverso cartas de orden",
        "readme_name": "LEEME.txt",
        "readme": """Gloria a Roma - archivos de impresion
Cada nombre de archivo termina con el numero de copias a imprimir, p. ej. (3x).
Cada carpeta contiene los anversos y sus reversos correspondientes de un tipo de carta:

1 Cartas de orden       un anverso por carta; TODAS comparten el unico reverso "Reverso cartas de orden".
2 Solares               doble cara: anverso = solar en la ciudad, reverso = solar fuera de la ciudad (rayado).
3 Bonus de comerciante  identica por ambas caras ("_back" es la misma imagen, impresa dos veces).
4 Lider                 identica por ambas caras.
5 Senador               anverso = espada, reverso = pluma.

PNG, 300 dpi, RGB con perfil sRGB, {bleed} mm de sangrado por cada lado, esquinas rectas
(se redondean al troquelar). Tamano de corte 63,5 x 88,9 mm (poker).
""",
    },
}


def packaging(language: str) -> dict:
    return PACKAGING.get(language, PACKAGING["en"])


def output_name(card: Card, suffix: str, language: str) -> str:
    return f"{card.key}{'_' + suffix if suffix else ''}_{language}({card.copies}x)"


def render_deck(renderer: Renderer, cards: list, include_order_back: bool = True):
    """Yields (relative path without extension, image) for every face of every card, grouped in
    one folder per card kind so fronts and backs are easy to pair. Kinds whose back equals the
    front (merchant bonus, leader) get an explicit "_back" copy."""
    pack = packaging(renderer.language)
    for card in cards:
        faces = renderer.render(card)
        if card.type in ("merchant_bonus", "leader"):
            faces = faces + [("back", faces[0][1])]
        for suffix, image in faces:
            yield f"{pack['folders'][card.type]}/{output_name(card, suffix, renderer.language)}", image
    order_copies = sum(c.copies for c in cards if c.type == "order")
    if include_order_back and order_copies:
        yield f"{pack['folders']['order']}/{pack['order_back']}({order_copies}x)", renderer.order_card_back()


def readme(renderer: Renderer) -> tuple:
    """(file name, text) of the packaging readme for the renderer's language."""
    pack = packaging(renderer.language)
    return pack["readme_name"], pack["readme"].format(bleed=renderer.geo.size.bleed_mm)


def to_print_rgb(image: Image.Image) -> Image.Image:
    """Flatten transparency onto white and drop the alpha channel: print shops want plain RGB."""
    flat = Image.new("RGB", image.size, (255, 255, 255))
    flat.paste(image, mask=image.split()[-1])
    return flat


def png_bytes(image: Image.Image) -> bytes:
    """Print-ready PNG: flattened RGB, 300 dpi, sRGB profile embedded."""
    buffer = io.BytesIO()
    to_print_rgb(image).save(buffer, "PNG", dpi=(DPI, DPI), icc_profile=SRGB_PROFILE)
    return buffer.getvalue()
