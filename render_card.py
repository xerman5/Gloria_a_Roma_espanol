"""Render cards to PNG.

    python3 render_card.py Academy                # English
    python3 render_card.py Academy Bar --lang es  # Spanish
    python3 render_card.py --all --lang es        # every card type that is implemented
    python3 render_card.py --list                 # deck contents and copy counts
"""

import argparse
from collections import Counter
from pathlib import Path

from gtr.data import load_cards
from gtr.render import DPI, CardGeometry, CardSize, Renderer


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
    parser.add_argument("--all", action="store_true", help="render every card")
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
    keys = list(renderer.cards) if args.all else args.cards
    if not keys:
        parser.error("give at least one card key, --all or --list")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def save(name, image):
        path = out_dir / f"{name}.png"
        image.save(path, dpi=(DPI, DPI))
        print(f"Wrote {path}")

    for key in keys:
        card = renderer.cards[key]
        for suffix, image in renderer.render(card):
            save(f"{key}{'_' + suffix if suffix else ''}_{args.lang}({card.copies}x)", image)
    if args.all:
        order_copies = sum(c.copies for c in renderer.cards.values() if c.type == "order")
        save(f"Order Back({order_copies}x)", renderer.order_card_back())


if __name__ == "__main__":
    main()
