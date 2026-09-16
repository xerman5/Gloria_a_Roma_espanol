# GtR — generador de cartas de Glory to Rome

Genera imágenes de cartas listas para imprimir (300 dpi, con sangrado) a partir de los assets en `assets/` y los datos en `data/`. Es un port a Python/Pillow del generador original en .NET, con soporte multi-idioma.
Nace del trabajo original de EMC85 que se encuentra aqui: https://github.com/ecm85/GtR


## Uso

```bash
pip install -r requirements.txt
python3 render_card.py --list                # contenido del mazo y copias (244 cartas, 68 distintas)
python3 render_card.py Academy               # una carta, en inglés
python3 render_card.py Academy Bar --lang es # varias, en español
python3 render_card.py --all --lang es       # todas las cartas (anverso y reverso) + reverso común
python3 render_card.py --all --bleed 2       # sangrado de 2 mm en vez de los 3 mm por defecto
```

Los PNG salen en `output/`, a 300 dpi. Tamaño póker (63,5 × 88,9 mm) más el sangrado por cada lado: con 3 mm, 820 × 1120 px. Las esquinas son rectas: el redondeo lo hace la imprenta al troquelar.

## Fuente de verdad: `data/cards.csv`

Una fila por carta distinta, con sus copias físicas. Columnas:

| columna | contenido |
|---|---|
| `key` | identificador único |
| `type` | `order`, `site`, `merchant_bonus`, `leader`, `jack` |
| `suit` | material/palo (`Brick`, `Concrete`, `Marble`, `Stone`, `Rubble`, `Wood`); vacío en líder y jack |
| `set` | `Standard`, `Republic`, `Imperium`, `Promo` (las 10 fan-made de BGG) |
| `copies` | copias a imprimir |
| `image`, `back_image` | ilustración, relativa a `assets/images/` sin extensión |
| `title_en`, `title_es` | título |
| `text_en`, `text_es` | texto |
| `back_text_en`, `back_text_es` | texto del reverso (solo sitios) |

Una celda `*_es` vacía usa el inglés. Para añadir un idioma, añade columnas `title_xx`, `text_xx`, `back_text_xx` aquí y `role_xx` en `suits.csv`.

`data/suits.csv` complementa con los 6 palos: valor (puntos, influencia y coste de sitio), color, iconos y nombre del rol por idioma. El nombre del material es el título de la carta de sitio del palo.

## Marcado del texto

`|palabra` sugiere un salto de línea, `||` fuerza un salto de párrafo. Los `|` se respetan solo si todas las líneas del párrafo caben; si alguna desborda, el párrafo se maqueta con salto automático (así los `|` ajustados para el inglés no dejan palabras huérfanas en español). Toda palabra en MAYÚSCULAS (y `x2`, `+N`) va en negrita; si es un rol o material, además en el color del palo.

## Estructura

- `gtr/data.py` — carga de CSV, acceso a textos por idioma.
- `gtr/render.py` — geometría, primitivas Pillow, maquetado de texto, `Renderer`.
- `assets/images/` — ilustraciones (reescaladas 4x con Upscayl); `assets/fonts/` — Neuzeit Grotesk.

## Pendiente

Montaje en hojas de 3×6 para imprentas que trabajan por pliegos.
