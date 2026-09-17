"""Render cards to PNG.

    python3 render_card.py Academy                       # English
    python3 render_card.py Academy Bar --lang es         # Spanish
    python3 render_card.py --all --lang es               # every card + the shared order-card back
    python3 render_card.py --all --sets Standard Republic --types order site
    python3 render_card.py --list                        # deck contents and copy counts
"""

import argparse
from collections import Counter
from pathlib import Path

from gtr.data import load_cards
from gtr.deck import CARD_TYPES, SETS, png_bytes, readme, render_deck, select_cards
from gtr.render import CardGeometry, CardSize, Renderer


def list_deck(cards):
    by_type = Counter()
    for c in cards.values():
        by_type[c.type] += c.copies
        print(f"{c.copies:3} x {c.key:<24} {c.type:<15} {c.suit:<9} {c.set}")
    print()
    for t, n in by_type.items():
        print(f"{n:4}  {t}")
    print(f"{sum(by_type.values()):4}  total")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cards", nargs="*", help="card keys (see data/cards.csv)")
    parser.add_argument("--all", action="store_true", help="render every card matching --sets/--types")
    parser.add_argument("--sets", nargs="+", choices=SETS, default=SETS, help="order-card sets to include")
    parser.add_argument("--types", nargs="+", choices=CARD_TYPES, default=CARD_TYPES, help="card types to include")
    parser.add_argument("--list", action="store_true", help="print the deck with copy counts and exit")
    parser.add_argument("--lang", default="en", help="language suffix used in data/cards.csv columns")
    parser.add_argument("--out", default="output", help="output directory")
    parser.add_argument("--bleed", type=float, default=CardSize.bleed_mm, metavar="MM",
                        help="bleed beyond the trim line on every side, in mm (default %(default)s, the usual print-shop spec)")
    args = parser.parse_args()

    if args.list:
        list_deck(load_cards())
        return

    renderer = Renderer(args.lang, CardGeometry(CardSize(bleed_mm=args.bleed)))
    if args.all:
        cards = select_cards(renderer.cards, args.sets, args.types)
    elif args.cards:
        cards = [renderer.cards[k] for k in args.cards]
    else:
        parser.error("give at least one card key, --all or --list")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, image in render_deck(renderer, cards, include_order_back=args.all):
        path = out_dir / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes(image))
        print(f"Wrote {path}")
    if args.all:
        name, text = readme(renderer)
        (out_dir / name).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
