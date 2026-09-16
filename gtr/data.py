import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_LANGUAGE = "en"


def _localized(row: dict, field: str, language: str) -> str:
    """`<field>_<language>` from a CSV row, falling back to English when empty or missing."""
    return row.get(f"{field}_{language}") or row.get(f"{field}_{DEFAULT_LANGUAGE}", "")


@dataclass(frozen=True)
class Suit:
    key: str
    value: int  # points, influence and site cost are the same number per suit
    color: tuple
    role_icon: str
    influence_icon: str
    _row: dict

    def role(self, language: str) -> str:
        return _localized(self._row, "role", language)


@dataclass(frozen=True)
class Card:
    key: str
    type: str  # order | site | merchant_bonus | leader | jack
    suit: str  # empty for leader/jack
    set: str
    copies: int
    image: str
    back_image: str
    _row: dict

    def title(self, language: str) -> str:
        return _localized(self._row, "title", language)

    def text(self, language: str) -> str:
        return _localized(self._row, "text", language)

    def back_text(self, language: str) -> str:
        return _localized(self._row, "back_text", language)


def _hex_to_rgba(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _read(name: str):
    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_suits() -> dict:
    return {
        r["key"]: Suit(r["key"], int(r["value"]), _hex_to_rgba(r["color"]), r["role_icon"], r["influence_icon"], r)
        for r in _read("suits.csv")
    }


def load_cards() -> dict:
    return {
        r["key"]: Card(r["key"], r["type"], r["suit"], r["set"], int(r["copies"]), r["image"], r["back_image"], r)
        for r in _read("cards.csv")
    }


def languages() -> list:
    with open(DATA_DIR / "cards.csv", encoding="utf-8-sig", newline="") as f:
        return [c[len("title_"):] for c in csv.DictReader(f).fieldnames if c.startswith("title_")]
