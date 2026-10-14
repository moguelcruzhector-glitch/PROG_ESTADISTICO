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
import itertools
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
        return "🥗"


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
            font-size: 2rem;
            font-weight: 800;
            color: var(--azul);
        }
        .hero-texto p {
            margin: 0.3rem 0 0;
            font-size: 1rem;
            color: var(--pizarra);
        }

        h2, h3 { color: var(--azul); }
        [data-testid="stCaptionContainer"] { color: var(--pizarra); }

        /* Tarjetas de resumen */
        [data-testid="stMetric"] {
            background: #ffffff;
            padding: 0.6rem 1rem;
            border-radius: 12px;
            border-left: 6px solid var(--azul);
            box-shadow: 0 4px 16px rgba(0, 56, 120, 0.12);
        }
        [data-testid="stMetricLabel"] { color: var(--pizarra); }
        [data-testid="stMetricValue"] { color: var(--azul); }

        /* Pestañas */
        button[data-baseweb="tab"] { font-weight: 600; color: #3a4a6b; }
        button[data-baseweb="tab"][aria-selected="true"] { color: var(--azul); }
        [data-baseweb="tab-highlight"] { background-color: var(--azul) !important; height: 3px; }

        /* Cada gráfica en una tarjeta blanca para que resalte */
        [data-testid="stPlotlyChart"], .stPlotlyChart {
            background: #ffffff;
            border-radius: 14px;
            border: 1px solid #d6e2f3;
            box-shadow: 0 4px 18px rgba(0, 56, 120, 0.12);
            padding: 0.4rem;
        }

        hr {
            background: linear-gradient(90deg, transparent, var(--azul), transparent);
            border: none;
            height: 2px;
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cargar_datos(archivo=None):
    """Carga el CSV (prueba varias codificaciones para evitar errores con acentos y eñes)"""
    try:
        if archivo is not None:
            df = None
            for codificacion in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    archivo.seek(0)  # volver al inicio antes de cada intento
                    df = pd.read_csv(archivo, encoding=codificacion)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                st.error("No se pudo leer el archivo (codificación no reconocida)")
                return None
        else:
            df = pd.read_csv("diana.csv")

        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def limpiar_columna(col_name):
    """Limpia nombres de columnas para hacerlos legibles"""
    return col_name.replace('_', ' ').title()


def explotar_valores_multiples(df, columna):
    """Explota valores separados por comas en una columna y retorna serie expandida"""
    valores_expandidos = []
    
    for val in df[columna]:
        # Saltar NaN o vacíos
        if pd.isna(val):
            continue
        
        val_str = str(val).strip()
        
        # --- EL TRUCO ESTÁ AQUÍ ---
        # Reemplazar la coma por un punto SOLO si está entre dos números (ej. "1,67" -> "1.67")
        val_str = re.sub(r'(\d),(\d)', r'\1.\2', val_str)
        
        if val_str == '' or val_str.lower() == 'ninguno':
            continue
        
        # Si tiene comas, SEPARAR CADA VALOR
        if ',' in val_str:
            # Dividir por coma y limpiar cada parte
            partes = val_str.split(',')
            for parte in partes:
                parte_limpia = parte.strip()
                # Solo agregar si no está vacío
                if parte_limpia and parte_limpia.lower() != 'ninguno':
                    valores_expandidos.append(parte_limpia)
        else:
            # Sin comas, agregar como está
            valores_expandidos.append(val_str)
    
    return pd.Series(valores_expandidos)


# Errores de ortografía conocidos del CSV: "texto mal escrito": "texto correcto"
CORRECCIONES = {
    "cardiovacular": "cardiovascular",
    r"^37$": "3/7",                     # frijoles: "37" era "3/7"
    r"(\d)(AM|PM)": r"\1 \2",          # "4:00PM" -> "4:00 PM"
    r"^Mercado, Supermercados$": "Mercado y supermercados",   # ambas = una sola respuesta
}

# Columnas donde la coma NO separa respuestas (cada celda es una sola respuesta)
COLUMNAS_SIN_SEPARAR = {"lugar donde los compra"}


def _normalizar(texto):
    """Minúsculas, sin acentos y sin espacios extra (energía -> energia)"""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r'\s+', ' ', texto).strip()


def unificar_categorias(serie):
    """Junta como una sola categoría los valores que solo difieren en
    espacios dobles, espacios al final, mayúsculas/minúsculas, acentos o
    errores de ortografía listados en CORRECCIONES."""
    def limpiar(v):
        v = re.sub(r'\s+', ' ', str(v)).strip()
        for mal, bien in CORRECCIONES.items():
            v = re.sub(mal, bien, v, flags=re.IGNORECASE)
        return v

    limpios = serie.map(limpiar)
    claves = limpios.map(_normalizar)
    # Etiqueta final: la forma más frecuente de cada grupo
    etiquetas = limpios.groupby(claves).agg(lambda s: s.value_counts().index[0])
    return claves.map(etiquetas)


# ---------------------------------------------------------------- COLORES
PALETA = ["#003878", "#2F80ED", "#00A6A6", "#F2B134", "#E4572E",
          "#7B61FF", "#17B890", "#FF7A90", "#586078", "#8FB8ED"]

# Colores con significado (clave = categoría en minúsculas y sin acentos)
COLORES_FIJOS = {
    # Sexo
    "femenino": "#F472B6", "mujer": "#F472B6",      # rosa
    "masculino": "#3B82F6", "hombre": "#3B82F6",    # azul
    # Sí / No / Tal vez
    "si": "#00B894", "no": "#FF7675", "tal vez": "#FDCB6E",
    # IMC
    "normal": "#00B894", "sobrepeso": "#FDCB6E",
    "obesidad": "#E17055", "obesidad 1": "#FF9F43",
    "obesidad 2": "#E17055", "obesidad 3": "#D63031",
    # ICC
    "riesgo cardiovascular bajo": "#55D68A",
    "riesgo cardiovascular moderado": "#FDCB6E",
    "riesgo cardiovascular alto": "#E17055",
    "riesgo cardiovascular muy alto": "#D63031",
    # Nivel de actividad física
    "muy bajo": "#D63031", "bajo": "#E17055", "moderado": "#FDCB6E",
    "alto": "#55D68A", "muy alto": "#00B894",
    # Estado emocional
    "feliz": "#FDCB6E", "triste": "#0984E3", "ansioso": "#A29BFE",
    "enojado": "#D63031", "frustrado": "#E17055", "deprimido": "#636E72",
}


def _mapa_colores(categorias, originales=None):
    """Color por categoría: fijo si tiene significado, si no, de la paleta."""
    originales = originales or categorias
    mapa = {}
    for j, (nombre, original) in enumerate(zip(categorias, originales)):
        mapa[nombre] = COLORES_FIJOS.get(_normalizar(original), PALETA[j % len(PALETA)])
    return mapa


# ---------------------------------------------------------------- DATOS
def buscar_columna(df, nombre):
    """Encuentra la columna aunque cambien espacios, mayúsculas o acentos."""
    clave = _normalizar(nombre)
    for c in df.columns:
        if _normalizar(c) == clave:
            return c
    return None


def buscar_columna_que_empiece(df, inicio):
    """Encuentra la columna cuyo nombre empieza con ese texto (ej. 'Ultima vez...')."""
    clave = _normalizar(inicio)
    for c in df.columns:
        if _normalizar(c).startswith(clave):
            return c
    return None


def conteos_columna(df, nombre, separar=True):
    """Cuenta las respuestas de una columna (separando por comas con la función original)."""
    col = buscar_columna(df, nombre)
    if col is None:
        st.info(f"No encontré la columna «{nombre}» en el archivo.")
        return None
    if (not separar) or _normalizar(col) in COLUMNAS_SIN_SEPARAR:
        datos = df[col].dropna().astype(str)
        datos = datos[datos.str.strip() != ""]
    else:
        datos = explotar_valores_multiples(df, col)
    if len(datos) == 0:
        st.warning(f"Sin datos para {nombre}")
        return None
    return unificar_categorias(datos).value_counts()


def contar_si_no(df, nombre):
    """(personas que dijeron Sí, personas que dijeron No)"""
    col = buscar_columna(df, nombre)
    if col is None:
        return 0, 0
    datos = df[col].dropna().map(_normalizar)
    return int((datos == "si").sum()), int((datos == "no").sum())


def _ordenar(conteos, orden_fijo=None):
    """Mayor a menor, o el orden indicado."""
    if orden_fijo:
        pos = {_normalizar(x): i for i, x in enumerate(orden_fijo)}
        return sorted(conteos.index, key=lambda c: pos.get(_normalizar(c), 99))
    return list(conteos.index)


# ---------------------------------------------------------------- GRÁFICAS
def _layout(fig, alto, titulo_size=14):
    fig.update_layout(
        height=alto,
        margin=dict(t=50, b=20, l=10, r=30),
        title_font_size=titulo_size,
        showlegend=False,
    )


def grafico_barras(conteos, titulo, horizontal=False, nombres_dentro=False,
                   orden_fijo=None, color_unico=None):
    """Barras con color por categoría. 'nombres_dentro' escribe el nombre dentro de la barra."""
    cats = _ordenar(conteos, orden_fijo)
    df_g = pd.DataFrame({'Categoría': cats, 'Cantidad': [int(conteos[c]) for c in cats]})
    mapa = _mapa_colores(cats)
    color_arg = {} if color_unico else dict(color='Categoría', color_discrete_map=mapa)

    if nombres_dentro:
        horizontal = True
        df_g['Texto'] = df_g['Categoría'] + "  ·  " + df_g['Cantidad'].astype(str)

    if horizontal:
        fig = px.bar(df_g, x='Cantidad', y='Categoría', orientation='h',
                     text='Texto' if nombres_dentro else 'Cantidad', title=titulo, **color_arg)
        fig.update_yaxes(autorange='reversed', title=None)
        fig.update_xaxes(title=None, showgrid=False)
        if nombres_dentro:
            fig.update_yaxes(showticklabels=False)
            fig.update_traces(textposition='inside', insidetextanchor='start',
                              constraintext='none', textangle=0)   # textangle=0: texto siempre horizontal
            maximo = max(df_g['Cantidad'])
            texto_color = {r['Categoría']: ("white" if r['Cantidad'] / maximo >= 0.45 else "#2d3436")
                           for _, r in df_g.iterrows()}
            fig.for_each_trace(lambda t: t.update(
                textfont=dict(color=texto_color.get(t.name, "white"), size=13)))
        else:
            fig.update_traces(textposition='outside', cliponaxis=False)
        alto = min(440, 110 + 34 * len(cats))
    else:
        fig = px.bar(df_g, x='Categoría', y='Cantidad', text='Cantidad', title=titulo, **color_arg)
        fig.update_xaxes(title=None, categoryorder='array', categoryarray=cats)
        fig.update_yaxes(title="Personas")
        fig.update_traces(textposition='outside', cliponaxis=False)
        alto = 360

    if color_unico:
        fig.update_traces(marker_color=color_unico)
    fig.update_layout(bargap=0.25)
    _layout(fig, alto)
    return fig


def grafico_pastel(conteos, titulo, etiquetas_en_grafica=True, abreviar=None, hole=0.45):
    """Pastel / dona. Con etiquetas_en_grafica muestra el nombre (diagnóstico) y el % sobre el pastel."""
    cats = list(conteos.index)
    nombres = [abreviar(c) for c in cats] if abreviar else cats
    df_g = pd.DataFrame({'Categoría': nombres, 'Cantidad': [int(conteos[c]) for c in cats]})
    mapa = _mapa_colores(nombres, cats)
    fig = px.pie(df_g, values='Cantidad', names='Categoría', title=titulo,
                 color='Categoría', color_discrete_map=mapa, hole=hole)
    if etiquetas_en_grafica:
        fig.update_traces(textinfo='label+percent', textposition='outside',
                          textfont_size=13, pull=0.02)
        fig.update_layout(height=380, margin=dict(t=60, b=30, l=60, r=60),
                          title_font_size=14, showlegend=False)
    else:
        fig.update_layout(height=380, margin=dict(t=60, b=20, l=20, r=20),
                          title_font_size=14, showlegend=True, legend=dict(x=1.0, y=1))
    return fig


def mostrar(fig, clave):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=clave)


# ---- Cada pregunta
def g_sexo(df):
    c = conteos_columna(df, "Sexo")
    return None if c is None else grafico_pastel(c, f"Sexo (n={int(c.sum())})")


def g_edad(df):
    col = buscar_columna(df, "Edad")
    if col is None:
        st.info("No encontré la columna «Edad».")
        return None
    edades = pd.to_numeric(df[col], errors='coerce').dropna()
    if len(edades) == 0:
        st.warning("Sin datos para Edad")
        return None
    ini, fin = int(edades.min() // 10 * 10), int(edades.max() // 10 * 10)
    rangos = {f"{a}-{a + 9}": int(((edades >= a) & (edades <= a + 9)).sum())
              for a in range(ini, fin + 1, 10)}
    conteos = pd.Series(rangos)
    return grafico_barras(conteos, f"Edad por rangos (n={len(edades)} · promedio {edades.mean():.0f} años)",
                          orden_fijo=list(conteos.index))


def g_ocupacion(df):
    c = conteos_columna(df, "Ocupacion")
    return None if c is None else grafico_barras(c, f"Ocupación (n={int(c.sum())})")


def g_imc(df):
    c = conteos_columna(df, "IMC")
    return None if c is None else grafico_pastel(c, f"IMC · diagnóstico (n={int(c.sum())})")


def g_icc(df):
    c = conteos_columna(df, "ICC")
    if c is None:
        return None
    return grafico_pastel(c, f"ICC · diagnóstico (n={int(c.sum())})",
                          abreviar=lambda x: x.replace("Riesgo cardiovascular ", "Riesgo "))


def _a_meses(texto):
    """'15 dias' -> 0.5 · '3 meses' -> 3 · '1 año y 4 meses' -> 16. None si no entiende."""
    t = _normalizar(texto)
    total, hallado = 0.0, False
    for num, unidad in re.findall(r'(\d+(?:\.\d+)?)\s*(dias?|semanas?|mes(?:es)?|anos?)', t):
        hallado = True
        n = float(num)
        if unidad.startswith("dia"):
            total += n / 30
        elif unidad.startswith("semana"):
            total += n * 7 / 30
        elif unidad.startswith("mes"):
            total += n
        else:
            total += n * 12
    return total if hallado else None


def g_desparasitacion(df):
    """Une las dos columnas: cuántas personas están desparasitadas (Sí/No)
    y cuánto tiempo hace de su última desparasitación."""
    col_d = buscar_columna(df, "Desparasitacion")
    col_t = buscar_columna_que_empiece(df, "Ultima vez")
    if col_d is None or col_t is None:
        st.info("No encontré las columnas de desparasitación.")
        return None

    estado = df[col_d].map(lambda v: None if pd.isna(v) else {"si": "Sí", "no": "No"}.get(_normalizar(v)))

    con_fecha = df[col_t].notna() & (df[col_t].astype(str).str.strip() != "")
    tiempo = pd.Series("Sin fecha registrada", index=df.index, dtype=object)
    if con_fecha.any():
        tiempo[con_fecha] = unificar_categorias(df.loc[con_fecha, col_t].astype(str)).values

    d = pd.DataFrame({"Desparasitado": estado, "Tiempo": tiempo}).dropna(subset=["Desparasitado"])
    if d.empty:
        st.warning("Sin datos de desparasitación")
        return None

    conteo = d.groupby(["Tiempo", "Desparasitado"]).size().reset_index(name="Personas")
    orden = sorted(d["Tiempo"].unique(),
                   key=lambda x: (x == "Sin fecha registrada", _a_meses(x) is None, _a_meses(x) or 0))
    si, no = int((d["Desparasitado"] == "Sí").sum()), int((d["Desparasitado"] == "No").sum())

    fig = px.bar(conteo, x="Tiempo", y="Personas", color="Desparasitado", text="Personas",
                 color_discrete_map={"Sí": "#00B894", "No": "#FF7675"},
                 category_orders={"Desparasitado": ["Sí", "No"]},
                 title=f"Desparasitación y tiempo desde la última vez (Sí: {si} · No: {no})")
    fig.update_xaxes(title="Última vez que se desparasitó", categoryorder="array",
                     categoryarray=orden, tickangle=-30)
    fig.update_yaxes(title="Personas")
    fig.update_traces(textposition="inside", textfont=dict(color="white", size=12))
    fig.update_layout(height=420, margin=dict(t=80, b=20, l=10, r=20), title_font_size=14,
                      bargap=0.25, barmode="stack",
                      legend=dict(orientation="h", y=1.12, x=0, title=None))
    return fig


def g_lugar_compra(df):
    c = conteos_columna(df, "Lugar donde los compra", separar=False)
    return None if c is None else grafico_barras(c, f"Lugar de compra (n={int(c.sum())})",
                                                 nombres_dentro=True)


# Frecuencia de alimentos: rangos que usó el equipo al capturar (3/7, 2/7, 1/7)
RANGOS_FRECUENCIA = {
    "3/7 · Carnes a Huevo": ["Carne de res", "Carne de puerco", "Pescado", "Pollo o gallina",
                             "Frutas", "Verduras", "Frijoles", "Lentejas", "Garbanzos", "Arroz",
                             "Leche", "Queso", "Crema", "Huevo"],
    "2/7 · Galletas a Energéticas": ["Galletas dulces", "Pan dulce", "Sabritas",
                                     "Refrescos embotellados", "Chocolates", "Dulces",
                                     "Bebidas energeticas"],
    "1/7 · Sopas a Sal": ["Sopas instantaneas", "Salchicha", "Jamon", "Tocino", "Chorizo",
                          "Rikopollo", "Knor", "Sal"],
}
COLORES_RANGOS = ["#003878", "#F2B134", "#00A6A6"]


def g_frecuencia_alimentos(df):
    total = len(df)
    filas = []
    for rango, alimentos in RANGOS_FRECUENCIA.items():
        parte = []
        for nombre in alimentos:
            col = buscar_columna(df, nombre)
            if col is None:
                continue
            marcados = int((df[col].notna() & (df[col].astype(str).str.strip() != "")).sum())
            parte.append((nombre, rango, marcados))
        filas += sorted(parte, key=lambda f: -f[2])   # dentro de cada rango, de más a menos
    if not filas:
        st.info("No encontré las columnas de alimentos.")
        return None
    df_g = pd.DataFrame(filas, columns=['Alimento', 'Frecuencia', 'Personas'])
    df_g['Texto'] = df_g['Personas'].astype(str) + " (" + (df_g['Personas'] / total * 100).round(0).astype(int).astype(str) + "%)"
    mapa = dict(zip(RANGOS_FRECUENCIA.keys(), COLORES_RANGOS))
    fig = px.bar(df_g, x='Alimento', y='Personas', color='Frecuencia', text='Texto',
                 color_discrete_map=mapa,
                 title=f"Alimentos que consumen, por frecuencia (n={total} personas)")
    fig.update_xaxes(title=None, categoryorder='array', categoryarray=list(df_g['Alimento']),
                     tickangle=-40)
    fig.update_yaxes(title="Personas")
    fig.update_traces(textposition='outside', cliponaxis=False, textfont_size=11)
    fig.update_layout(height=520, margin=dict(t=90, b=20, l=10, r=20), title_font_size=14,
                      bargap=0.2, legend=dict(orientation='h', y=1.12, x=0, title=None))
    return fig


def g_educacion(df):
    c = conteos_columna(df, "Cual")
    if c is None:
        return None
    si, no = contar_si_no(df, "Educacion nutricional")
    return grafico_barras(c, f"Tipo de educación nutricional (Sí: {si} · No: {no})",
                          nombres_dentro=True)


def g_emocional(df):
    c = conteos_columna(df, "Estado emocional frecuente")
    return None if c is None else grafico_barras(c, f"Estado emocional frecuente (n={int(c.sum())})",
                                                 horizontal=True)


def g_realiza_af(df):
    c = conteos_columna(df, "Realiza AF")
    return None if c is None else grafico_barras(c, "¿Realiza actividad física?")


def g_tipo_af(df):
    c = conteos_columna(df, "Cual.1")
    return None if c is None else grafico_barras(c, "Tipo de actividad física", horizontal=True)


def g_nivel_af(df):
    c = conteos_columna(df, "Nivel de AF")
    if c is None:
        return None
    return grafico_barras(c, "Nivel de actividad física",
                          orden_fijo=["Muy bajo", "Bajo", "Moderado", "Alto", "Muy alto"])


def g_traslado(df):
    c = conteos_columna(df, "Traslado")
    return None if c is None else grafico_barras(c, "Medio de traslado", horizontal=True)


def g_interes(df):
    """Mismo estilo de dona de antes, solo con colores nuevos."""
    c = conteos_columna(df, "Interes al Ejercicio")
    if c is None:
        return None
    return grafico_pastel(c, "Distribución: Interés Al Ejercicio",
                          etiquetas_en_grafica=False, hole=0.3)


def g_cultivos(df):
    """Se deja tal cual estaba: dona con la paleta original."""
    c = conteos_columna(df, "Cultiva algun alimento")
    if c is None:
        return None
    df_g = pd.DataFrame({'Categoría': c.index, 'Cantidad': c.values})
    fig = px.pie(df_g, values='Cantidad', names='Categoría',
                 title="Distribución: Cultiva Algun Alimento",
                 color_discrete_sequence=px.colors.qualitative.Set3, hole=0.3)
    fig.update_layout(height=380, margin=dict(t=60, b=20, l=20, r=20), title_font_size=16,
                      showlegend=True, legend=dict(x=1.0, y=1))
    return fig


def g_salud_emocional(df):
    """Barras horizontales: frecuencia de cada estado emocional, desglosada por sexo."""
    col_e = buscar_columna(df, "Estado emocional frecuente")
    col_s = buscar_columna(df, "Sexo")
    if col_e is None:
        st.info("No encontré la columna de estado emocional.")
        return None

    filas = []
    for idx in df.index:
        for emocion in explotar_valores_multiples(df.loc[[idx]], col_e):
            filas.append({"idx": idx, "Emoción": emocion})

    if not filas:
        st.warning("Sin datos para estado emocional")
        return None

    d = pd.DataFrame(filas)
    d["Emoción"] = unificar_categorias(d["Emoción"])

    if col_s is not None:
        sexo = df.loc[d["idx"], col_s].fillna("Sin dato").astype(str)
        d["Sexo"] = unificar_categorias(sexo).values
    else:
        d["Sexo"] = "Sin dato"

    conteos = d["Emoción"].value_counts()
    categorias = list(conteos.index)
    resumen = (
        d.groupby(["Emoción", "Sexo"])
         .size()
         .reset_index(name="Personas")
    )

    mapa_sexo = _mapa_colores(sorted(resumen["Sexo"].unique()))
    fig = px.bar(
        resumen,
        x="Personas",
        y="Emoción",
        color="Sexo",
        text="Personas",
        barmode="group",
        category_orders={"Emoción": categorias[::-1]},
        color_discrete_map=mapa_sexo,
        title=(
            "Salud emocional: frecuencia de estados emocionales por sexo "
            f"(n={d['idx'].nunique()} personas)"
        ),
        hover_data={"Personas": True, "Emoción": True, "Sexo": True},
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title="Personas", showgrid=True)
    fig.update_yaxes(title=None, categoryorder="array", categoryarray=categorias[::-1])
    fig.update_layout(
        height=min(560, 150 + 45 * len(categorias)),
        margin=dict(t=75, b=30, l=10, r=35),
        title_font_size=14,
        bargap=0.25,
        legend=dict(orientation="h", y=1.1, x=0, title=None),
    )
    return fig


def g_animales(df):
    c = conteos_columna(df, "Cuales")
    if c is None:
        return None
    si, no = contar_si_no(df, "Cuenta con algun animal en casa")
    return grafico_barras(c, f"Animales en casa (Sí cuentan: {si} · No: {no})", horizontal=True)


# ---------------------------------------------------------------- CONSTRUCTOR DE GRÁFICAS
# Permite elegir pregunta, tipo de gráfica, filtros y colores desde menús (sin tocar código).
COLUMNAS_OCULTAS = {"folio"}

TIPOS_GRAFICA = ["Barras verticales", "Barras horizontales", "Pastel", "Dona",
                 "Histograma", "Dispersión"]

ORDENES = ["Mayor a menor", "Menor a mayor", "A-Z", "Como aparece en la base"]

PALETAS_USUARIO = {
    "Automática (colores con significado)": None,
    "Azules UNICACH": ["#003878", "#2F80ED", "#8FB8ED", "#586078", "#00A6A6", "#F2B134", "#E4572E", "#7B61FF"],
    "Vibrante": ["#6C5CE7", "#00B894", "#FD79A8", "#FDCB6E", "#0984E3", "#E17055", "#00CEC9", "#A29BFE"],
    "Pastel suave": ["#8DD3C7", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#FFED6F"],
    "Semáforo": ["#00B894", "#FDCB6E", "#E17055", "#D63031", "#0984E3", "#6C5CE7"],
    "Rosa y azul": ["#F472B6", "#3B82F6", "#A78BFA", "#34D399", "#FBBF24", "#F87171"],
}


def _limpiar_texto(v):
    """Misma limpieza de unificar_categorias, para una sola respuesta."""
    v = re.sub(r'\s+', ' ', str(v)).strip()
    for mal, bien in CORRECCIONES.items():
        v = re.sub(mal, bien, v, flags=re.IGNORECASE)
    return v


def _valores_celda(valor, es_numerica, separar):
    """Lista de respuestas de una celda (varias si hay comas y se pide separar)."""
    if pd.isna(valor):
        return []
    if es_numerica:
        return [float(valor)]
    if separar:
        return [str(x) for x in explotar_valores_multiples(pd.DataFrame({"c": [valor]}), "c")]
    texto = str(valor).strip()
    return [texto] if texto else []


def tabla_larga(df, roles, separar):
    """Una fila por respuesta. roles = {"X": columna, "Y": columna, "C": columna}"""
    numericas = {r: pd.api.types.is_numeric_dtype(df[c]) for r, c in roles.items()}
    filas = []
    for _, fila in df.iterrows():
        listas = []
        for r, c in roles.items():
            vals = _valores_celda(fila[c], numericas[r], separar)
            if not vals and r == "C":
                vals = ["Sin dato"]
            listas.append(vals)
        for combo in itertools.product(*listas):
            filas.append(dict(zip(roles.keys(), combo)))
    tabla = pd.DataFrame(filas)
    if not tabla.empty:
        for r in roles:
            if not numericas[r]:
                tabla[r] = unificar_categorias(tabla[r])
    return tabla, numericas


def _colores_para(categorias, paleta):
    secuencia = PALETAS_USUARIO.get(paleta)
    categorias = list(categorias)
    if secuencia is None:
        return _mapa_colores(categorias)
    return {c: secuencia[i % len(secuencia)] for i, c in enumerate(categorias)}


def _ordenar_usuario(totales, orden, aparicion):
    if orden == "Mayor a menor":
        return list(totales.sort_values(ascending=False, kind="stable").index)
    if orden == "Menor a mayor":
        return list(totales.sort_values(ascending=True, kind="stable").index)
    if orden == "A-Z":
        return sorted(totales.index, key=_normalizar)
    return [c for c in aparicion if c in totales.index]


def _a_posicion(serie, rng):
    """Numérica -> tal cual. Texto -> posición 0,1,2... con un poco de separación."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float), None
    cats = list(serie.value_counts().index)
    pos = serie.map({c: i for i, c in enumerate(cats)}).astype(float)
    return pos + rng.uniform(-0.22, 0.22, len(serie)), cats


def construir_figura(df, cfg):
    """Devuelve (figura, tabla_de_datos) según las opciones elegidas en el constructor."""
    tipo = cfg["tipo"]
    roles = {"X": cfg["x"]}
    if tipo == "Dispersión":
        if cfg["y"] is None:
            st.info("Elige la pregunta del eje Y.")
            return None, None
        roles["Y"] = cfg["y"]
    if cfg["color"] is not None and tipo not in ("Pastel", "Dona"):
        roles["C"] = cfg["color"]

    tabla, num = tabla_larga(df, roles, cfg["separar"])
    if tabla.empty:
        st.warning("No hay datos con las opciones elegidas.")
        return None, None

    nombre_x = limpiar_columna(cfg["x"].strip())
    tiene_color = "C" in roles
    mostrar_leyenda = cfg["leyenda"]

    # ------------------------------------------------ Pastel / Dona / Barras
    if tipo in ("Barras verticales", "Barras horizontales", "Pastel", "Dona"):
        natural = None
        if num["X"]:   # preguntas numéricas (ej. Edad) se agrupan en rangos
            paso = int(cfg["paso"])
            inicios = (tabla["X"] // paso * paso).astype(int)
            tabla["X"] = inicios.map(lambda a: f"{a}-{a + paso - 1}")
            natural = list(pd.Series(tabla["X"].values, index=inicios.values).sort_index().drop_duplicates())

        claves = ["X"] + (["C"] if tiene_color else [])
        resumen = tabla.groupby(claves).size().reset_index(name="Cantidad")
        resumen["Porcentaje"] = resumen["Cantidad"] / resumen["Cantidad"].sum() * 100
        valor = "Porcentaje" if cfg["unidad"] == "Porcentaje" else "Cantidad"
        eje_valor = "% de respuestas" if valor == "Porcentaje" else "Personas"
        totales = resumen.groupby("X")["Cantidad"].sum()
        aparicion = list(dict.fromkeys(tabla["X"]))
        orden = natural or _ordenar_usuario(totales, cfg["orden"], aparicion)
        resumen["Texto"] = resumen[valor].map(
            lambda v: f"{v:.0f}%" if valor == "Porcentaje" else str(int(v)))

        titulo = cfg["titulo"] or (f"{nombre_x}" + (f" según {limpiar_columna(cfg['color'].strip())}" if tiene_color else "")
                                   + f" (n={int(resumen['Cantidad'].sum())})")
        if tiene_color:
            mapa = _colores_para(dict.fromkeys(resumen["C"]), cfg["paleta"])
        else:
            mapa = _colores_para(orden, cfg["paleta"])

        if tipo in ("Pastel", "Dona"):
            fig = px.pie(resumen, values=valor, names="X", color="X", color_discrete_map=mapa,
                         category_orders={"X": orden}, hole=0.45 if tipo == "Dona" else 0, title=titulo)
            if cfg["valores"]:
                fig.update_traces(textinfo="label+percent", textposition="outside")
            fig.update_layout(showlegend=mostrar_leyenda)
        else:
            horizontal = tipo == "Barras horizontales"
            comunes = dict(color="C" if tiene_color else "X", color_discrete_map=mapa,
                           text="Texto" if cfg["valores"] else None, title=titulo,
                           category_orders={"X": orden},
                           barmode="stack" if cfg["modo"] == "Apiladas" else "group")
            if horizontal:
                fig = px.bar(resumen, x=valor, y="X", orientation="h", **comunes)
                fig.update_yaxes(autorange="reversed", title=None)
                fig.update_xaxes(title=eje_valor)
            else:
                fig = px.bar(resumen, x="X", y=valor, **comunes)
                fig.update_xaxes(title=nombre_x)
                fig.update_yaxes(title=eje_valor)
            apilada = tiene_color and cfg["modo"] == "Apiladas"
            fig.update_traces(textposition="inside" if apilada else "outside", cliponaxis=False)
            fig.update_layout(bargap=0.25, showlegend=mostrar_leyenda and tiene_color)
        tabla_datos = resumen.drop(columns=["Texto"]).rename(
            columns={"X": cfg["x"], "C": cfg["color"]})

    # ------------------------------------------------ Histograma
    elif tipo == "Histograma":
        if not num["X"]:
            st.info("El histograma necesita una pregunta numérica (por ejemplo Edad).")
            return None, None
        titulo = cfg["titulo"] or f"Distribución de {nombre_x} (n={len(tabla)})"
        if tiene_color:
            mapa = _colores_para(dict.fromkeys(tabla["C"]), cfg["paleta"])
            fig = px.histogram(tabla, x="X", color="C", color_discrete_map=mapa,
                               nbins=int(cfg["intervalos"]), title=titulo)
        else:
            fig = px.histogram(tabla, x="X", nbins=int(cfg["intervalos"]), title=titulo)
            fig.update_traces(marker_color=(PALETAS_USUARIO.get(cfg["paleta"]) or ["#003878"])[0])
        fig.update_xaxes(title=nombre_x)
        fig.update_yaxes(title="Personas")
        fig.update_layout(bargap=0.05, showlegend=mostrar_leyenda and tiene_color)
        tabla_datos = tabla.rename(columns={"X": cfg["x"], "C": cfg["color"]})

    # ------------------------------------------------ Dispersión
    else:
        nombre_y = limpiar_columna(cfg["y"].strip())
        rng = np.random.default_rng(1)
        pos_x, cats_x = _a_posicion(tabla["X"], rng)
        pos_y, cats_y = _a_posicion(tabla["Y"], rng)
        d = pd.DataFrame({"Eje X": pos_x.values, "Eje Y": pos_y.values,
                          "Valor X": tabla["X"].astype(str).values,
                          "Valor Y": tabla["Y"].astype(str).values})
        titulo = cfg["titulo"] or f"{nombre_y} según {nombre_x} (n={len(d)})"
        hover = {"Eje X": False, "Eje Y": False, "Valor X": True, "Valor Y": True}
        if tiene_color:
            d["Color"] = tabla["C"].values
            mapa = _colores_para(dict.fromkeys(d["Color"]), cfg["paleta"])
            fig = px.scatter(d, x="Eje X", y="Eje Y", color="Color", color_discrete_map=mapa,
                             hover_data=hover, title=titulo)
        else:
            fig = px.scatter(d, x="Eje X", y="Eje Y", hover_data=hover, title=titulo)
            fig.update_traces(marker_color=(PALETAS_USUARIO.get(cfg["paleta"]) or ["#003878"])[0])
        fig.update_traces(marker=dict(size=12, opacity=0.85, line=dict(width=1, color="white")))
        fig.update_xaxes(title=nombre_x)
        fig.update_yaxes(title=nombre_y)
        if cats_x:
            fig.update_xaxes(tickmode="array", tickvals=list(range(len(cats_x))), ticktext=cats_x)
        if cats_y:
            fig.update_yaxes(tickmode="array", tickvals=list(range(len(cats_y))), ticktext=cats_y)

        if cfg["tendencia"]:
            if cats_x is None and cats_y is None:
                if len(d) >= 3 and d["Eje X"].nunique() > 1 and d["Eje Y"].nunique() > 1:
                    m, b = np.polyfit(d["Eje X"], d["Eje Y"], 1)
                    r = np.corrcoef(d["Eje X"], d["Eje Y"])[0, 1]
                    xs = np.array([d["Eje X"].min(), d["Eje X"].max()])
                    fig.add_scatter(x=xs, y=m * xs + b, mode="lines", name=f"Tendencia (r = {r:.2f})",
                                    line=dict(color="#003878", width=3, dash="dash"))
                else:
                    st.caption("No hay suficientes datos distintos para trazar la tendencia.")
            elif (cats_x is None) != (cats_y is None):
                if cats_y is not None:   # promedio de X por cada categoría de Y
                    medias = d.groupby("Valor Y")["Eje X"].mean()
                    xs_l, ys_l = [float(medias[c]) for c in cats_y], list(range(len(cats_y)))
                else:                    # promedio de Y por cada categoría de X
                    medias = d.groupby("Valor X")["Eje Y"].mean()
                    ys_l, xs_l = [float(medias[c]) for c in cats_x], list(range(len(cats_x)))
                fig.add_scatter(x=xs_l, y=ys_l, mode="lines+markers", name="Promedio por categoría",
                                line=dict(color="#003878", width=2, dash="dash"),
                                marker=dict(symbol="diamond", size=12, color="#003878"))
            else:
                st.caption("La línea de tendencia necesita al menos una pregunta numérica.")
        fig.update_layout(showlegend=mostrar_leyenda)
        tabla_datos = tabla.rename(columns={"X": cfg["x"], "Y": cfg["y"], "C": cfg["color"]})

    fig.update_layout(height=int(cfg["alto"]), margin=dict(t=70, b=30, l=20, r=20),
                      title_font_size=16, legend=dict(orientation="h", y=1.1, x=0, title=None))
    return fig, tabla_datos


def _indice_de(opciones, nombre, defecto=0):
    for i, o in enumerate(opciones):
        if _normalizar(o) == _normalizar(nombre):
            return i
    return defecto


def aplicar_filtro(df, columna, seleccion):
    """Se queda con las personas cuya respuesta coincide con alguna de las opciones elegidas."""
    sel = {_normalizar(_limpiar_texto(s)) for s in seleccion}

    def cumple(v):
        if pd.isna(v):
            return False
        vals = explotar_valores_multiples(pd.DataFrame({"c": [v]}), "c")
        return any(_normalizar(_limpiar_texto(x)) in sel for x in vals)

    return df[df[columna].map(cumple)]


def pestana_constructor(df):
    st.markdown("### 🛠️ Arma tu propia gráfica")
    st.caption("Elige la pregunta, el tipo de gráfica y las opciones. "
               "La gráfica se actualiza sola, sin tocar código.")

    opciones = [c for c in df.columns if _normalizar(c) not in COLUMNAS_OCULTAS]
    izq, der = st.columns([1, 2.4])

    with izq:
        st.markdown("**1 · Datos**")
        x = st.selectbox("Pregunta principal", opciones,
                         index=_indice_de(opciones, "Sexo"), key="cons_x")
        tipo = st.selectbox("Tipo de gráfica", TIPOS_GRAFICA, key="cons_tipo")
        x_numerica = pd.api.types.is_numeric_dtype(df[x])

        y = None
        if tipo == "Dispersión":
            y = st.selectbox("Pregunta del eje Y", opciones,
                             index=_indice_de(opciones, "Edad"), key="cons_y")

        color = None
        if tipo not in ("Pastel", "Dona"):
            elegido = st.selectbox("Dividir / colorear por (opcional)", ["(ninguna)"] + opciones,
                                   key="cons_color")
            color = None if elegido == "(ninguna)" else elegido

        separar = st.checkbox("Separar respuestas con comas", value=True, key="cons_sep",
                              help="Si alguien respondió 'Feliz, Ansioso', cuenta cada emoción por separado.")

        st.markdown("**2 · Filtro (opcional)**")
        col_filtro = st.selectbox("Mostrar solo personas con…", ["(sin filtro)"] + opciones, key="cons_filtro")
        df_f = df
        if col_filtro != "(sin filtro)":
            if pd.api.types.is_numeric_dtype(df[col_filtro]):
                minimo, maximo = float(df[col_filtro].min()), float(df[col_filtro].max())
                if minimo < maximo:
                    rango = st.slider("Rango", minimo, maximo, (minimo, maximo), key="cons_rango")
                    df_f = df[df[col_filtro].between(rango[0], rango[1])]
            else:
                disponibles = conteos_columna(df, col_filtro)
                if disponibles is not None:
                    opciones_f = list(disponibles.index)
                    elegidos = st.multiselect("Valores a incluir", opciones_f, default=opciones_f,
                                              key="cons_valores")
                    df_f = aplicar_filtro(df, col_filtro, elegidos) if elegidos else df.iloc[0:0]

        st.markdown("**3 · Opciones de la gráfica**")
        unidad, orden, modo, paso, intervalos, tendencia = "Personas", ORDENES[0], "Agrupadas", 10, 8, True
        if tipo in ("Barras verticales", "Barras horizontales", "Pastel", "Dona"):
            if tipo in ("Barras verticales", "Barras horizontales"):
                unidad = st.radio("Mostrar", ["Personas", "Porcentaje"], horizontal=True, key="cons_unidad")
            if color is not None and tipo in ("Barras verticales", "Barras horizontales"):
                modo = st.radio("Barras", ["Agrupadas", "Apiladas"], horizontal=True, key="cons_modo")
            if x_numerica:
                paso = st.slider("Tamaño de cada rango", 1, 20, 10, key="cons_paso")
            else:
                orden = st.selectbox("Orden", ORDENES, key="cons_orden")
        if tipo == "Histograma":
            intervalos = st.slider("Número de intervalos", 3, 30, 8, key="cons_intervalos")
        if tipo == "Dispersión":
            tendencia = st.checkbox("Mostrar línea de tendencia", value=True, key="cons_tendencia")

        with st.expander("🎨 Apariencia"):
            paleta = st.selectbox("Colores", list(PALETAS_USUARIO.keys()), key="cons_paleta")
            titulo = st.text_input("Título (vacío = automático)", value="", key="cons_titulo")
            valores = st.checkbox("Mostrar valores sobre la gráfica", value=True, key="cons_valores_chk")
            leyenda = st.checkbox("Mostrar leyenda", value=True, key="cons_leyenda")
            alto = st.slider("Alto de la gráfica", 300, 800, 450, step=10, key="cons_alto")

    with der:
        if df_f.empty:
            st.warning("Con ese filtro no queda ninguna persona. Cambia las opciones.")
            return
        cfg = dict(x=x, y=y, color=color, tipo=tipo, separar=separar, unidad=unidad, orden=orden,
                   modo=modo, paso=paso, intervalos=intervalos, tendencia=tendencia,
                   paleta=paleta, titulo=titulo.strip(), valores=valores, leyenda=leyenda, alto=alto)
        fig, tabla_datos = construir_figura(df_f, cfg)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, key="constructor_grafica")
            st.caption(f"Personas incluidas: {len(df_f)} de {len(df)}")
            with st.expander("📋 Ver tabla de datos"):
                st.dataframe(tabla_datos)
                st.download_button("📥 Descargar esta tabla", tabla_datos.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="grafica_personalizada.csv", mime="text/csv",
                                   key="cons_descarga")


# ---------------------------------------------------------------- APP
def main():
    aplicar_estilo()

    # Header
    st.markdown(
        '<div class="hero">'
        + _img_tag("logo_unicach.png", "Universidad Autónoma de Ciencias y Artes de Chiapas")
        + '<div class="hero-texto"><h1>Análisis Nutricional</h1>'
        + '<p>Clínica de Nutrición UNICACH · Resultados de la encuesta</p></div>'
        + _img_tag("logo_clinica.png", "Clínica de Nutrición UNICACH")
        + '</div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown("## 📤 Cargar Encuesta")

        archivo = st.file_uploader("Sube tu archivo CSV aquí", type=["csv"])

        if archivo:
            st.success(f"✅ {archivo.name}")
        else:
            st.info("Selecciona un archivo CSV para comenzar")

    # Cargar datos
    if archivo is None:
        st.info("👆 Sube tu archivo CSV en el panel izquierdo para comenzar el análisis")
        return

    df = cargar_datos(archivo=archivo)

    if df is None or df.empty:
        st.error("No se pudieron cargar los datos. Verifica que sea un archivo CSV válido")
        return

    # Información general
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Respuestas", len(df))
    with col2:
        st.metric("Total de Preguntas", len(df.columns))
    with col3:
        st.metric("Datos Completos", f"{(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100:.1f}%")

    tabs = st.tabs(["👥 Demografía", "⚖️ Estado Nutricional", "💊 Salud y Educación",
                    "🛒 Alimentación", "🏃 Actividad Física", "💭 Salud Emocional",
                    "🌱 Cultivos y Animales", "🛠️ Constructor de gráficas"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar(g_sexo(df), "sexo")
        with c2:
            mostrar(g_edad(df), "edad")
        with c3:
            mostrar(g_ocupacion(df), "ocupacion")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar(g_imc(df), "imc")
        with c2:
            mostrar(g_icc(df), "icc")

    with tabs[2]:
        c1, c2 = st.columns([3, 2])
        with c1:
            mostrar(g_desparasitacion(df), "desparasitacion")
        with c2:
            mostrar(g_educacion(df), "educacion")

    with tabs[3]:
        c1, c2 = st.columns([1, 2])
        with c1:
            mostrar(g_lugar_compra(df), "lugar_compra")
        with c2:
            mostrar(g_frecuencia_alimentos(df), "frecuencia_alimentos")
        st.caption("Cada barra cuenta las personas que marcaron ese alimento. "
                   "Los rangos 3/7, 2/7 y 1/7 son los de la tabla de captura.")

    with tabs[4]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar(g_realiza_af(df), "realiza_af")
        with c2:
            mostrar(g_tipo_af(df), "tipo_af")
        with c3:
            mostrar(g_nivel_af(df), "nivel_af")
        c4, c5 = st.columns(2)
        with c4:
            mostrar(g_traslado(df), "traslado")
        with c5:
            mostrar(g_interes(df), "interes")

    with tabs[5]:
        mostrar(g_salud_emocional(df), "salud_emocional")
        st.caption("Las barras muestran cuántas veces se reportó cada estado emocional, "
                   "desglosado por sexo. Si una persona indicó varias emociones, cada una se cuenta.")

    with tabs[6]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar(g_cultivos(df), "cultivos")
        with c2:
            mostrar(g_animales(df), "animales")

    with tabs[7]:
        pestana_constructor(df)

    # Descarga del resumen (un solo clic)
    resumen = pd.DataFrame({
        'Pregunta': df.columns,
        'Tipo de Dato': [
            'Numérico' if pd.api.types.is_numeric_dtype(df[col]) else 'Texto'
            for col in df.columns
        ],
        'Valores Válidos': [len(df[col].dropna()) for col in df.columns],
        'Valores Únicos': [df[col].nunique() for col in df.columns]
    })
    with st.sidebar:
        st.markdown("---")
        st.download_button(
            label="📥 Descargar resumen",
            data=resumen.to_csv(index=False),
            file_name="resumen_analisis.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
