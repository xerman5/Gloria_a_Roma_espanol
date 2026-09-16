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


def output_name(card: Card, suffix: str, language: str) -> str:
    return f"{card.key}{'_' + suffix if suffix else ''}_{language}({card.copies}x)"


def render_deck(renderer: Renderer, cards: list, include_order_back: bool = True):
    """Yields (file name without extension, image) for every face of every card."""
    for card in cards:
        for suffix, image in renderer.render(card):
            yield output_name(card, suffix, renderer.language), image
    order_copies = sum(c.copies for c in cards if c.type == "order")
    if include_order_back and order_copies:
        yield f"Order Back({order_copies}x)", renderer.order_card_back()


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
