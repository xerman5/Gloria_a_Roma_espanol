"""Card rendering with Pillow. Layout mirrors the original .NET GloryToRomeImageCreator:
everything is positioned as a percentage of the card's usable rectangle so it scales with card size."""

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .data import Card, Suit, load_cards, load_suits

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets" / "images"
FONTS_DIR = REPO_ROOT / "assets" / "fonts"

DPI = 300
_DPI_FACTOR = DPI / 96  # original font sizes were specified at 96 dpi
HEADER_FONT_SIZE = int(18.5 * _DPI_FACTOR)
BODY_FONT_SIZE = int(10 * _DPI_FACTOR)

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)

INFLUENCE_PCT = 0.13
ROLE_ICON_PCT = 0.18
SET_INDICATOR_PCT = 0.10
TEXT_COLUMN_PCT = 0.66  # title/body width; leaves ~6% clear of the role letters and set circles
ROLE_ICON_ASPECT = 190 / 140

SITE_COST_REGION_PCT = 0.36      # bottom strip of the site front with the stripes and cost text
SITE_RESOURCE_SECTION_PCT = 0.35  # band above it holding the material icon
SITE_RESOURCE_PADDING_PCT = 0.15
SITE_COIN_WIDTH_PCT = 0.20
SITE_COIN_PADDING_PCT = 0.05
STRIPES_PER_CARD = 16
JACK_IMAGE_OFFSET_PCT = 0.30
JACK_TEXT_COLOR = (208, 208, 208, 255)

# Original text used U+2005 between words for GDI+ kerning; we keep it for fidelity.
WORD_SPACER = "\u2005"  # four-per-em space

# Bold: any ALL-CAPS word (role/material names, THINKER, JACK, VP...) or x2 / +N.
BOLD_WORD = re.compile(r"^[^\w]*(?:[A-ZÁÉÍÓÚÑ]{2,}|x2|\+\d)[^\w]*$")

FONT_BODY = ImageFont.truetype(str(FONTS_DIR / "NeuzeitGro-RegModified.ttf"), BODY_FONT_SIZE)
FONT_BODY_BOLD = ImageFont.truetype(str(FONTS_DIR / "NeuzeitGro-BolModified.ttf"), BODY_FONT_SIZE)
FONT_HEADER = FONT_BODY_BOLD.font_variant(size=HEADER_FONT_SIZE)
FONT_SITE = FONT_BODY.font_variant(size=int(13 * _DPI_FACTOR))


# --- geometry -----------------------------------------------------------------

MM_PER_INCH = 25.4


def mm_to_px(mm: float) -> int:
    return round(mm / MM_PER_INCH * DPI)


@dataclass(frozen=True)
class CardSize:
    """Trim size of the card plus print margins, in millimetres. Defaults: poker card, 3 mm bleed."""
    width_mm: float = 63.5
    height_mm: float = 88.9
    bleed_mm: float = 3.0
    safe_margin_mm: float = 1.6  # keep-out inside the trim line where nothing important is drawn


class CardGeometry:
    """Pixel rectangles for a portrait card: full (trim + bleed), trim, and usable (trim inset by safe margin)."""

    def __init__(self, size: CardSize = CardSize()):
        self.size = size
        trim_w, trim_h = mm_to_px(size.width_mm), mm_to_px(size.height_mm)
        bleed, safe = mm_to_px(size.bleed_mm), mm_to_px(size.safe_margin_mm)

        self.width = trim_w + bleed * 2
        self.height = trim_h + bleed * 2
        self.full = (0, 0, self.width, self.height)
        self.trim = (bleed, bleed, trim_w, trim_h)
        self.usable = (bleed + safe, bleed + safe, trim_w - safe * 2, trim_h - safe * 2)


# --- image primitives ---------------------------------------------------------

def load_png(image: str) -> Image.Image:
    """`image` is a path relative to assets/images without extension, e.g. 'CardImages/Academy'."""
    return Image.open(ASSETS_DIR / f"{image}.png").convert("RGBA")


def paste_scaled(canvas: Image.Image, image: str, x: int, y: int, width: int, height: int):
    img = load_png(image).resize((max(1, width), max(1, height)), Image.LANCZOS)
    canvas.alpha_composite(img, (x, y))


def paste_full_width(canvas: Image.Image, image: str, x: int, y: int, width: int,
                     center_on_content: bool = False) -> int:
    """Scale to `width` keeping aspect ratio; returns the drawn height.
    With center_on_content, the artwork's non-transparent bounding box is centered horizontally."""
    img = load_png(image)
    height = width * img.height // img.width
    img = img.resize((width, height), Image.LANCZOS)
    if center_on_content:
        bbox = img.split()[-1].getbbox()
        if bbox:
            x += int(width / 2 - (bbox[0] + bbox[2]) / 2)
    canvas.paste(img, (x, y), img)
    return height


def paste_fit_centered(canvas: Image.Image, image: str, x: int, y: int, max_w: int, max_h: int):
    """Scale to fit inside max_w × max_h keeping aspect ratio, centered in that box."""
    img = load_png(image)
    aspect = img.width / img.height
    if max_w / max_h <= aspect:
        w, h = max_w, round(max_w / aspect)
    else:
        w, h = round(max_h * aspect), max_h
    img = img.resize((max(1, w), max(1, h)), Image.LANCZOS)
    canvas.alpha_composite(img, (x + (max_w - w) // 2, y + (max_h - h) // 2))


def draw_stripes(canvas: Image.Image, color, rising: bool, clip=None):
    """Diagonal stripes across the card in the suit color, 45°, one stripe-width apart.
    `rising` draws them bottom-left → top-right, optionally clipped to `clip` (x, y, w, h)."""
    width, height = canvas.size
    thickness = width // STRIPES_PER_CARD
    stroke = int((thickness ** 2 / 2) ** 0.5)
    extra = 25
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for x in range(-2 * width + 10, width, thickness * 2):
        if rising:
            draw.line((x - extra, height + extra, height + x + extra, -extra), fill=color, width=stroke)
        else:
            draw.line((x - extra, -extra, height + x + extra, height + extra), fill=color, width=stroke)
    if clip:
        cx, cy, cw, ch = clip
        mask = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(mask).rectangle((cx, cy, cx + cw, cy + ch), fill=255)
        layer.putalpha(Image.composite(layer.split()[-1], mask, mask))
    canvas.alpha_composite(layer)


def draw_translucent(canvas: Image.Image, paint):
    """ImageDraw ignores alpha when painting onto RGBA, so paint on a layer and composite it."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    paint(ImageDraw.Draw(layer))
    canvas.alpha_composite(layer)


# --- text ---------------------------------------------------------------------

@dataclass
class TextFragment:
    text: str
    font: ImageFont.FreeTypeFont
    color: tuple
    forces_newline: bool = False
    paragraph_break: bool = False


def _measure(draw, fragment: TextFragment, extra_w=0, extra_h=0):
    bbox = draw.textbbox((0, 0), fragment.text, font=fragment.font)
    ascent, descent = fragment.font.getmetrics()
    return bbox[2] - bbox[0] + extra_w, ascent + descent + extra_h


def _wrap(max_width, measured):
    """Greedy word wrap ignoring forced breaks."""
    lines, current, width = [], [], 0
    for item in measured:
        if current and width + item[1] > max_width:
            lines.append(current)
            current, width = [], 0
        current.append(item)
        width += item[1]
    if current:
        lines.append(current)
    return lines


def _group_by_line(max_width, measured):
    """Forced breaks (`|`) are honored only when every line of their paragraph fits; otherwise the
    whole paragraph is re-wrapped automatically, so breaks tuned for one language don't strand
    single words in a longer one. Paragraph breaks (`||`) are always kept."""
    paragraphs, current = [], []
    for item in measured:
        if item[0].paragraph_break:
            paragraphs.append(current)
            paragraphs.append([item])
            current = []
        else:
            current.append(item)
    paragraphs.append(current)

    lines = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        segments, segment = [], []
        for item in paragraph:
            if item[0].forces_newline and segment:
                segments.append(segment)
                segment = []
            segment.append(item)
        segments.append(segment)
        if all(sum(m[1] for m in seg) <= max_width for seg in segments):
            lines.extend(segments)
        else:
            lines.extend(_wrap(max_width, paragraph))
    return lines


def draw_fragments_centered(canvas, fragments, rect, center_vertically: bool, loose: bool, background_alpha: int):
    """Word-wraps fragments into `rect` and draws each line horizontally centered over a translucent
    white box. Vertical centering uses the real ink extent, not font metrics, so the visible block sits
    evenly between its neighbours. `loose` adds the per-word padding the original used for body text."""
    draw = ImageDraw.Draw(canvas)
    x, y, w, h = rect
    extra_w, extra_h = (13, 8) if loose else (0, 0)
    measured = [(f, *_measure(draw, f, extra_w, extra_h)) for f in fragments]
    lines = _group_by_line(w, measured)
    total_height = sum(max(m[2] for m in line) for line in lines)
    total_width = max(sum(m[1] for m in line) for line in lines)
    min_x = x + (w // 2 - total_width // 2)

    def paint(target_draw, top):
        current_y = top
        for line in lines:
            current_x = x + (w // 2 - sum(m[1] for m in line) // 2)
            for fragment, fw, _ in line:
                target_draw.text((current_x, current_y), fragment.text, font=fragment.font, fill=fragment.color)
                current_x += fw
            current_y += max(m[2] for m in line)
        return current_y

    top = y
    if center_vertically:
        probe = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        paint(ImageDraw.Draw(probe), y)
        ink = probe.getbbox()
        if ink:
            top = y + (y + h // 2) - (ink[1] + ink[3]) // 2
    draw_translucent(canvas, lambda d: d.rectangle(
        (min_x, top, min_x + total_width, top + total_height), fill=(255, 255, 255, background_alpha)))
    return paint(draw, top)  # bottom of the drawn text block


def header_fragments(text: str, color=BLACK):
    """Card/role headers: one word per line, uppercase."""
    return [TextFragment(w, FONT_HEADER, color, i > 0) for i, w in enumerate(text.upper().split(" "))]


# --- renderer -----------------------------------------------------------------

class Renderer:
    """Renders cards for one language. `|word` forces a line break, `||` a paragraph break;
    ALL-CAPS words are bold, and role/material names are additionally colored by suit."""

    def __init__(self, language: str, geometry: CardGeometry = None):
        self.language = language
        self.geo = geometry or CardGeometry()
        self.suits = load_suits()
        self.cards = load_cards()
        self.suit_keywords = {}
        for suit in self.suits.values():
            self.suit_keywords[suit.role(language).upper()] = suit
            self.suit_keywords[self.material_name(suit).upper()] = suit

    def material_name(self, suit: Suit) -> str:
        """The material name is the title of the suit's site card, so it lives in one place only."""
        return next(c for c in self.cards.values() if c.type == "site" and c.suit == suit.key).title(self.language)

    def body_fragments(self, text: str, default_color=BLACK):
        return [self._fragment(word, default_color) for word in text.split(" ")]

    def _fragment(self, word: str, default_color) -> TextFragment:
        forces_newline = word.startswith("|")
        paragraph_break = word.startswith("||")
        word = WORD_SPACER if paragraph_break else word.lstrip("|")
        suit = next((s for k, s in self.suit_keywords.items() if k in word), None)
        bold = suit is not None or BOLD_WORD.match(word) is not None
        color = suit.color if suit else default_color
        return TextFragment(word + WORD_SPACER, FONT_BODY_BOLD if bold else FONT_BODY, color,
                            forces_newline, paragraph_break)

    def _blank_card(self, background=WHITE):
        canvas = Image.new("RGBA", (self.geo.width, self.geo.height), background)
        return canvas, ImageDraw.Draw(canvas)

    def _title(self, canvas, text, rect, alpha, color=BLACK) -> int:
        return draw_fragments_centered(canvas, header_fragments(text, color), rect,
                                       center_vertically=False, loose=False, background_alpha=alpha)

    def _body(self, canvas, text, rect, alpha, color=BLACK) -> int:
        return draw_fragments_centered(canvas, self.body_fragments(text, color), rect,
                                       center_vertically=True, loose=True, background_alpha=alpha)

    def render(self, card: Card) -> list:
        """Returns [(suffix, image)] — one entry per printable face of the card."""
        if card.type == "order":
            return [("", self.order_card_front(card))]
        if card.type == "site":
            return [("", self.site_front(card)), ("back", self.site_back(card))]
        if card.type == "merchant_bonus":
            return [("", self.merchant_bonus(card))]
        if card.type == "leader":
            return [("", self.leader(card))]
        if card.type == "jack":
            return [("", self.jack(card, card.image)), ("back", self.jack(card, card.back_image))]
        raise NotImplementedError(f"unknown card type '{card.type}'")

    def _coins(self, canvas, count: int, y: int):
        """`count` coins in a row, centered horizontally in the usable area."""
        ux, uy, uw, uh = self.geo.usable
        coin = int(uw * SITE_COIN_WIDTH_PCT)
        padding = int(uw * SITE_COIN_PADDING_PCT)
        offset_count = -count / 2
        x_offset = int(offset_count * coin + (offset_count + 0.5) * padding)
        center = ux + uw // 2
        for i in range(count):
            paste_scaled(canvas, "Misc/Coin", center + x_offset + i * (coin + padding), y, coin, coin)

    def _material_icon_band(self, canvas, card: Card, bottom_region_pct: float):
        """Material icon centered in the band that sits above a bottom region of the given height."""
        ux, uy, uw, uh = self.geo.usable
        fh = self.geo.height
        padding = int(fh * SITE_RESOURCE_PADDING_PCT)
        section = int(fh * SITE_RESOURCE_SECTION_PCT)
        icon_h = section - padding
        y = fh - (int(fh * bottom_region_pct) + padding // 2 + icon_h)
        paste_fit_centered(canvas, card.image, ux, y, uw, icon_h)

    def site_front(self, card: Card) -> Image.Image:
        suit = self.suits[card.suit]
        canvas, draw = self._blank_card()
        ux, uy, uw, uh = self.geo.usable
        fw, fh = self.geo.width, self.geo.height

        # Striped cost strip along the bottom with the cost text on a white label
        cost_h = int(fh * SITE_COST_REGION_PCT)
        draw_stripes(canvas, suit.color, rising=True, clip=(0, fh - cost_h, fw, cost_h))
        cost_text = card.text(self.language)
        tw, th = draw.textbbox((0, 0), cost_text, font=FONT_SITE)[2], sum(FONT_SITE.getmetrics())
        tx, ty = fw // 2 - tw // 2, int((fh - cost_h) + cost_h * 0.1)
        pad = th // 4
        draw.rectangle((tx - pad, ty, tx + tw + pad, ty + th), fill=WHITE)
        draw.text((tx, ty), cost_text, font=FONT_SITE, fill=BLACK)

        self._material_icon_band(canvas, card, SITE_COST_REGION_PCT)

        # Material name just above the icon band
        name = card.title(self.language).upper()
        name_h = sum(FONT_HEADER.getmetrics())
        name_y = fh - (cost_h + int(fh * SITE_RESOURCE_SECTION_PCT) + name_h)
        draw_translucent(canvas, lambda d: d.rectangle((ux, name_y, ux + uw, name_y + name_h), fill=(255, 255, 255, 100)))
        name_w = draw.textbbox((0, 0), name, font=FONT_HEADER)[2]
        draw.text((ux + uw // 2 - name_w // 2, name_y), name, font=FONT_HEADER, fill=BLACK)

        self._coins(canvas, suit.value, uy)
        return canvas

    def site_back(self, card: Card) -> Image.Image:
        suit = self.suits[card.suit]
        canvas, draw = self._blank_card()
        ux, uy, uw, uh = self.geo.usable
        draw_stripes(canvas, suit.color, rising=False)

        name = card.title(self.language).upper()
        subtitle = card.back_text(self.language)
        name_h = sum(FONT_HEADER.getmetrics())
        sub_h = sum(FONT_SITE.getmetrics())
        top = uy + uh // 2 - (name_h + sub_h) // 2
        box_w = int(uw * 0.6)
        draw.rectangle((ux + (uw - box_w) // 2, top - name_h // 2, ux + (uw + box_w) // 2, top + name_h + sub_h + sub_h // 2), fill=WHITE)
        name_w = draw.textbbox((0, 0), name, font=FONT_HEADER)[2]
        sub_w = draw.textbbox((0, 0), subtitle, font=FONT_SITE)[2]
        draw.text((ux + uw // 2 - name_w // 2, top), name, font=FONT_HEADER, fill=BLACK)
        draw.text((ux + uw // 2 - sub_w // 2, top + name_h), subtitle, font=FONT_SITE, fill=BLACK)
        return canvas

    def merchant_bonus(self, card: Card) -> Image.Image:
        canvas, draw = self._blank_card()
        ux, uy, uw, uh = self.geo.usable
        fh = self.geo.height
        title_bottom = self._title(canvas, card.title(self.language), (ux + uw // 5, uy + int(uw * 0.05), 3 * uw // 5, uh), alpha=0)
        self._coins(canvas, 3, max(uy + int(uw * 0.26), title_bottom + int(uw * 0.03)))
        self._material_icon_band(canvas, card, 0.30)
        self._body(canvas, card.text(self.language), (ux, fh - int(fh * 0.35), uw, int(fh * 0.25)), alpha=0)
        return canvas

    def leader(self, card: Card) -> Image.Image:
        canvas, draw = self._blank_card()
        ux, uy, uw, uh = self.geo.usable
        fx, fy, fw, fh = self.geo.full
        image_bottom = fy + paste_full_width(canvas, card.image, fx, fy, fw)
        self._title(canvas, card.title(self.language), (ux, uy + int(uw * 0.05), uw, uh), alpha=100)
        influence = int(uw * INFLUENCE_PCT)
        self._body(canvas, card.text(self.language), (ux, image_bottom, uw, (uy + uh) - (influence + image_bottom)), alpha=200)
        return canvas

    def jack(self, card: Card, image: str) -> Image.Image:
        canvas, draw = self._blank_card(background=BLACK)
        ux, uy, uw, uh = self.geo.usable
        fx, fy, fw, fh = self.geo.full
        image_top = fy + int(fh * JACK_IMAGE_OFFSET_PCT)
        image_bottom = image_top + paste_full_width(canvas, image, fx, image_top, fw)
        self._title(canvas, card.title(self.language), (ux, uy + int(uw * 0.15), uw, uh), alpha=0, color=JACK_TEXT_COLOR)
        self._body(canvas, card.text(self.language), (ux, image_bottom, uw, (uy + uh) - image_bottom), alpha=0, color=JACK_TEXT_COLOR)
        return canvas

    def order_card_back(self) -> Image.Image:
        canvas, draw = self._blank_card(background=BLACK)
        ux, uy, uw, uh = self.geo.usable
        logo_w, logo_h = int(uw * (1 - 0.14)), int(uh * 0.3)
        logo = load_png("Misc/GloryToRome").resize((logo_w, logo_h), Image.LANCZOS)
        canvas.alpha_composite(logo, (ux + int(uw * 0.07), uy + int(uh * 0.15)))
        canvas.alpha_composite(logo.rotate(180), (ux + int(uw * 0.07), uy + uh - int(uh * 0.45)))
        sep_w, sep_h = int(uw * 0.4), int(uh * 0.05)
        paste_scaled(canvas, "Misc/OrderBackSeparator", ux + uw // 2 - sep_w // 2, uy + uh // 2 - sep_h // 2, sep_w, sep_h)
        return canvas

    def order_card_front(self, card: Card) -> Image.Image:
        suit = self.suits[card.suit]
        canvas, draw = self._blank_card()
        ux, uy, uw, uh = self.geo.usable
        fx, fy, fw, fh = self.geo.full

        image_bottom = fy + paste_full_width(canvas, card.image, fx, fy, fw, center_on_content=True)

        # Role icon with its name spelled vertically underneath
        icon_w = int(uw * ROLE_ICON_PCT)
        icon_h = int(icon_w * ROLE_ICON_ASPECT)
        paste_scaled(canvas, suit.role_icon, ux, uy, icon_w, icon_h)
        letters = [TextFragment(ch, FONT_HEADER, suit.color, True) for ch in suit.role(self.language).upper()]
        letter_w = max(_measure(draw, f)[0] for f in letters)
        draw_fragments_centered(canvas, letters, (ux + int(icon_w / 2 - letter_w / 2), uy + icon_h, letter_w, uh),
                                center_vertically=False, loose=False, background_alpha=200)

        # Title
        # Text column: centered on the card, with breathing room from the side columns.
        text_w = int(uw * TEXT_COLUMN_PCT)
        text_x = ux + (uw - text_w) // 2
        draw_fragments_centered(canvas, header_fragments(card.title(self.language)),
                                (text_x, uy + int(uw * 0.05), text_w, uh),
                                center_vertically=False, loose=False, background_alpha=100)

        # Bottom band: material name at the right, influence coins at the left (original size and spacing).
        # Only the text's cap height bounds the body text above; the coins may rise past it.
        material = self.material_name(suit).upper() + WORD_SPACER
        mat_w, mat_h = _measure(draw, TextFragment(material, FONT_HEADER, suit.color))
        mat_y = uy + uh - mat_h
        draw.text((ux + uw - mat_w, mat_y), material, font=FONT_HEADER, fill=suit.color)
        band_top = mat_y + draw.textbbox((0, 0), material, font=FONT_HEADER)[1]
        coin = int(uw * INFLUENCE_PCT)
        for i in range(suit.value):
            paste_scaled(canvas, suit.influence_icon, ux + coin * i, uy + uh - coin, coin, coin)

        # Set indicator: one circle per point, with the expansion icon inside for non-standard sets
        circle = int(uw * SET_INDICATOR_PCT)
        halo = int(circle * 1.2)
        icon = int(circle * 0.85)
        for i in range(suit.value):
            cx = ux + uw - circle
            cy = uy + i * circle + (int(circle * 0.2) * i)
            hx, hy = cx - (halo - circle) // 2, cy - (halo - circle) // 2
            draw_translucent(canvas, lambda d: d.ellipse((hx, hy, hx + halo, hy + halo), fill=(255, 255, 255, 200)))
            draw.ellipse((cx, cy, cx + circle, cy + circle), fill=suit.color)
            if card.set != "Standard":
                paste_scaled(canvas, f"Misc/{card.set}", cx + (circle - icon) // 2, cy + (circle - icon) // 2, icon, icon)

        # Body text, between artwork and the bottom band
        text_top = image_bottom
        text_h = band_top - text_top
        if text_h < 0:
            text_top -= uh // 2
            text_h = band_top - text_top
        draw_fragments_centered(canvas, self.body_fragments(card.text(self.language)),
                                (text_x, text_top, text_w, text_h),
                                center_vertically=True, loose=True, background_alpha=200)

        return canvas
