"""Deck selection and batch rendering shared by the CLI and the web app."""

from .data import Card
from .render import Renderer

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
