"""
Dashboard Especializado para Encuestas de Nutrición
Diseñado para Nutriólogos - Un gráfico por pregunta
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import re
import unicodedata
import base64
from pathlib import Path
from functools import lru_cache

# Configuración
CARPETA = Path(__file__).parent


def _icono_pagina():
    """Usa el logo de la Clínica como ícono de la pestaña; si no está, un emoji."""
    try:
        from PIL import Image
        return Image.open(CARPETA / "logo_clinica.png")
    except Exception:
        return None


st.set_page_config(
    page_title="Clínica de Nutrición UNICACH",
    page_icon=_icono_pagina(),
    layout="wide",
    initial_sidebar_state="expanded",
)


@lru_cache(maxsize=None)
def _img_tag(nombre_archivo, alt):
    """Imagen incrustada en el HTML. Si el archivo no está junto al código, no muestra nada."""
    try:
        datos = base64.b64encode((CARPETA / nombre_archivo).read_bytes()).decode()
        return f'<img class="hero-logo" src="data:image/png;base64,{datos}" alt="{alt}">'
    except Exception:
        return ""


def aplicar_estilo():
    """Estilo con los azules de los logos (Clínica de Nutrición y UNICACH)"""
    st.markdown(
        """
        <style>
        :root {
            --azul: #003878;
            --azul-oscuro: #0B2A5B;
            --pizarra: #586078;
            --fondo-claro: #e9eff8;
        }

        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #eaf0f9 0%, #d3e0f1 100%);
            background-attachment: fixed;
        }
        [data-testid="stHeader"] { background: transparent; }

        [data-testid="stMainBlockContainer"] {
            background: transparent;
            padding: 1rem 1.5rem;
            margin: 0.5rem;
            color: #1F2A44;
        }

        /* Panel lateral */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B2A5B 0%, #003878 100%);
        }
        [data-testid="stSidebar"] * { color: #f2f6fc; }

        /* Encabezado con logos */
        .hero {
            background: #ffffff;
            border-radius: 16px;
            border-bottom: 5px solid var(--azul);
            padding: 0.8rem 1.8rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.2rem;
            flex-wrap: wrap;
            box-shadow: 0 8px 26px rgba(0, 56, 120, 0.18);
        }
        .hero-logo { height: 92px; width: auto; }
        .hero-texto { text-align: center; flex: 1; min-width: 240px; }
        .hero-texto h1 {
            margin: 0;
