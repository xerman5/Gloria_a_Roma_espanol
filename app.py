"""Streamlit front-end: pick language, sets, card types and bleed; download a zip of PNGs.

    streamlit run app.py
"""

import io
import zipfile

import streamlit as st

from gtr.data import languages, load_cards
from gtr.deck import CARD_TYPES, SETS, png_bytes, render_deck, select_cards
from gtr.render import CardGeometry, CardSize, Renderer

LANGUAGE_NAMES = {"en": "English", "es": "Español"}
SET_LABELS = {
    "Standard": "Base",
    "Republic": "Modo República",
    "Imperium": "Modo Imperio",
    "Promo": "Expansión fan-made (BGG)",
}
TYPE_LABELS = {
    "order": "Cartas de orden",
    "site": "Sitios",
    "merchant_bonus": "Bonus de comerciante",
    "leader": "Líder",
    "jack": "Jack / Senador",
}

st.set_page_config(page_title="Gloria a Roma — generador de cartas", page_icon="🏛️")
st.title("Gloria a Roma — generador de cartas")
st.caption("PNG RGB a 300 dpi con perfil sRGB, listos para imprenta. El nombre de cada fichero incluye las copias a imprimir.")

with st.sidebar:
    st.header("Configuración")
    language = st.selectbox("Idioma", languages(), format_func=lambda l: LANGUAGE_NAMES.get(l, l),
                            index=languages().index("es") if "es" in languages() else 0)
    sets = st.multiselect("Sets de cartas de orden", SETS, default=["Standard", "Republic", "Imperium"],
                          format_func=SET_LABELS.get)
    types = st.multiselect("Tipos de carta", CARD_TYPES, default=CARD_TYPES, format_func=TYPE_LABELS.get)
    bleed = st.number_input("Sangrado (mm por lado)", min_value=0.0, max_value=10.0, value=CardSize.bleed_mm,
                            step=0.5, help="3 mm es el estándar de imprenta. La línea de corte queda dentro.")
    include_back = st.checkbox("Incluir reverso común de cartas de orden", value=True)

renderer = Renderer(language, CardGeometry(CardSize(bleed_mm=bleed)))
selected = select_cards(renderer.cards, sets, types)
copies = sum(c.copies for c in selected)

st.subheader("Mazo seleccionado")
st.write(f"**{len(selected)} cartas distintas · {copies} cartas físicas** · "
         f"{renderer.geo.width} × {renderer.geo.height} px por carta")

with st.expander("Vista previa de una carta"):
    preview_key = st.selectbox("Carta", [c.key for c in selected] or ["—"],
                               format_func=lambda k: renderer.cards[k].title(language) if k in renderer.cards else k)
    if preview_key in renderer.cards:
        faces = renderer.render(renderer.cards[preview_key])
        cols = st.columns(len(faces))
        for col, (suffix, image) in zip(cols, faces):
            col.image(image, caption=suffix or "anverso", width="stretch")

if st.button("Generar zip", type="primary", disabled=not selected):
    buffer = io.BytesIO()
    progress = st.progress(0.0, text="Renderizando…")
    total = sum(2 if c.type in ("site", "jack") else 1 for c in selected) + (1 if include_back else 0)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for i, (name, image) in enumerate(render_deck(renderer, selected, include_back), start=1):
            zf.writestr(f"{name}.png", png_bytes(image))
            progress.progress(min(i / total, 1.0), text=f"Renderizando… {name}")
    progress.empty()
    st.success(f"Listo: {total} imágenes.")
    st.download_button("Descargar zip", buffer.getvalue(), file_name=f"gloria_a_roma_{language}.zip",
                       mime="application/zip", type="primary")
